"""AC5 - 쓰기 권한 분리 writer.

Popper는 자기 소유 디렉토리(~/.claude/popper/) 밖에 절대 쓰지 않는다.
사용자 CLAUDE.md 본문과 라이브 settings.json은 무변경이며, 유일한 예외인
@import 한 줄은 import_permission_granted 동의 레코드가 인자로 전달될 때만
파일 끝에 추가된다(멱등). manifest에 기록된 마지막 쓰기 content hash와
디스크 내용이 불일치하면(수기 편집) silent overwrite 대신 감지 신호
(최강 strike 신호)를 반환하고 쓰기를 전면 중단한다.

@import 한 줄 제거가 전체 롤백 지점이다 - 사용자 파일에는 그 한 줄 외
어떤 바이트도 추가/변경하지 않는다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from popper.atomic import atomic_write_bytes, atomic_write_text
from popper.compiler import (
    MANIFEST_JSON,
    MANIFEST_VERSION,
    POPPER_MD,
    SETTINGS_JSON,
    content_hash,
    default_base_dir,
)
from popper.conflict import ConsentKind, ConsentRecord
from popper.locking import base_lock, target_lock

logger = logging.getLogger(__name__)

# manifest가 content hash를 기록/대조하는 산출물 (manifest.json 자신은 제외)
HASHED_OUTPUTS = (POPPER_MD, SETTINGS_JSON)

# 수기 편집 감지 신호 - 사용자가 규칙 본문을 직접 고쳤다는 최강 strike 신호
MANUAL_EDIT_STRIKE = "manual_edit_strike"

DETECT_MANUAL_EDIT = "manual_edit"
DETECT_MISSING = "missing"
DETECT_UNREADABLE_MANIFEST = "unreadable_manifest"

IMPORT_ADDED = "added"
IMPORT_REMOVED = "removed"
IMPORT_ALREADY_PRESENT = "already_present"
IMPORT_NOT_PRESENT = "not_present"
IMPORT_NO_PERMISSION = "permission_missing"
IMPORT_INVALID_PERMISSION = "invalid_permission"
IMPORT_SUBJECT_MISMATCH = "permission_subject_mismatch"
IMPORT_TARGET_MISSING = "claude_md_missing"


class OwnershipViolation(RuntimeError):
    """소유 디렉토리 밖 또는 보호된 사용자 파일에 대한 쓰기 시도."""


def _now(now: str | None = None) -> str:
    if now is not None:
        return now
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True, slots=True)
class ManualEditDetection:
    """manifest 기록 해시와 디스크 내용의 불일치 - 수기 편집 감지 한 건."""

    path: str
    recorded_hash: str | None
    actual_hash: str | None
    reason: str
    signal: str = MANUAL_EDIT_STRIKE
    detected_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "path": self.path,
            "recorded_hash": self.recorded_hash,
            "actual_hash": self.actual_hash,
            "reason": self.reason,
            "detected_at": self.detected_at,
        }


@dataclass(frozen=True, slots=True)
class WriteOutcome:
    """write_outputs 반환값 - 착지 경로 또는 수기 편집 감지 신호."""

    base_dir: Path
    written: tuple[Path, ...] = ()
    detections: tuple[ManualEditDetection, ...] = ()

    @property
    def blocked(self) -> bool:
        return bool(self.detections)


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    """ensure_import/remove_import 반환값."""

    path: Path
    line: str
    changed: bool
    reason: str


class OwnedWriter:
    """Popper 단독 소유 디렉토리 writer.

    모든 쓰기는 base_dir 내부로 강제되고, 사용자 CLAUDE.md와 라이브
    settings.json은 쓰기 대상에서 원천 차단된다. 유일한 사용자 파일 변경은
    ensure_import의 @import 한 줄 추가뿐이며 허가 레코드를 요구한다.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        claude_md_path: Path | None = None,
        live_settings_path: Path | None = None,
    ) -> None:
        home_claude = Path.home() / ".claude"
        self.base_dir = (base_dir if base_dir is not None else default_base_dir()).resolve()
        self.claude_md_path = (
            claude_md_path if claude_md_path is not None else home_claude / "CLAUDE.md"
        ).resolve()
        self.live_settings_path = (
            live_settings_path
            if live_settings_path is not None
            else home_claude / "settings.json"
        ).resolve()

    def path(self, name: str) -> Path:
        return self.base_dir / name

    def import_line(self) -> str:
        """CLAUDE.md에 들어갈 @import 한 줄 - POPPER.md 착지 경로의 순수 함수."""
        target = self.base_dir / POPPER_MD
        try:
            rel = target.relative_to(Path.home())
        except ValueError:
            return f"@{target.as_posix()}"
        return f"@~/{rel.as_posix()}"

    def _guard(self, name: str | Path) -> Path:
        """쓰기 대상 경로를 소유 디렉토리 내부로 강제한다."""
        candidate = Path(name)
        target = candidate if candidate.is_absolute() else self.base_dir / candidate
        resolved = target.resolve()
        if resolved == self.base_dir or not resolved.is_relative_to(self.base_dir):
            raise OwnershipViolation(f"소유 디렉토리 밖 쓰기 거부: {resolved}")
        if resolved in (self.claude_md_path, self.live_settings_path):
            raise OwnershipViolation(f"보호된 사용자 파일 쓰기 거부: {resolved}")
        return resolved

    def write_file(self, name: str | Path, body: str) -> Path:
        """소유 디렉토리 내부에만 쓴다 - 밖이면 OwnershipViolation."""
        target = self._guard(name)
        with base_lock(self.base_dir):
            return atomic_write_text(target, body)

    def detect_manual_edits(self) -> tuple[ManualEditDetection, ...]:
        """manifest의 마지막 쓰기 해시와 디스크 내용을 대조한다."""
        manifest_path = self.base_dir / MANIFEST_JSON
        if not manifest_path.exists():
            return ()
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("manifest 파싱 실패: %s", manifest_path, exc_info=True)
            return (
                ManualEditDetection(
                    path=str(manifest_path),
                    recorded_hash=None,
                    actual_hash=None,
                    reason=DETECT_UNREADABLE_MANIFEST,
                ),
            )

        detections: list[ManualEditDetection] = []
        outputs = manifest.get("outputs", {})
        if not isinstance(outputs, Mapping):
            outputs = {}
        for name in HASHED_OUTPUTS:
            entry = outputs.get(name)
            if not isinstance(entry, Mapping):
                continue
            recorded = entry.get("content_hash")
            if not recorded:
                continue
            target = self.base_dir / name
            if not target.exists():
                detections.append(
                    ManualEditDetection(
                        path=str(target),
                        recorded_hash=str(recorded),
                        actual_hash=None,
                        reason=DETECT_MISSING,
                    )
                )
                continue
            actual = content_hash(target.read_text(encoding="utf-8"))
            if actual != recorded:
                detections.append(
                    ManualEditDetection(
                        path=str(target),
                        recorded_hash=str(recorded),
                        actual_hash=actual,
                        reason=DETECT_MANUAL_EDIT,
                    )
                )
        return tuple(detections)

    def _write_outputs_unlocked(
        self,
        documents: Mapping[str, str],
        *,
        now: str | None = None,
    ) -> WriteOutcome:
        """산출물을 소유 디렉토리에 쓴다 - 수기 편집 감지 시 쓰기 전면 중단."""
        unknown = set(documents) - set(HASHED_OUTPUTS)
        if unknown:
            raise OwnershipViolation(f"소유 계약 밖 산출물 이름: {sorted(unknown)}")

        detections = self.detect_manual_edits()
        if detections:
            for detection in detections:
                logger.warning(
                    "수기 편집 감지 - silent overwrite 중단: %s (%s)",
                    detection.path,
                    detection.reason,
                )
            return WriteOutcome(base_dir=self.base_dir, detections=detections)

        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "generated_at": _now(now),
            "owned_dir": str(self.base_dir),
            "outputs": {
                name: {"content_hash": content_hash(body)}
                for name, body in documents.items()
            },
        }
        written: list[Path] = []
        for name, body in documents.items():
            written.append(self.write_file(name, body))
        written.append(self.write_file(MANIFEST_JSON, _canonical(manifest)))
        logger.info("popper 산출물 착지: %s", self.base_dir)
        return WriteOutcome(base_dir=self.base_dir, written=tuple(written))

    def write_outputs(
        self,
        documents: Mapping[str, str],
        *,
        now: str | None = None,
    ) -> WriteOutcome:
        """감지와 전체 산출물 교체를 하나의 프로세스 간 임계 구역에서 수행한다."""
        with base_lock(self.base_dir):
            return self._write_outputs_unlocked(documents, now=now)

    def _ensure_import_unlocked(
        self, permission: ConsentRecord | None = None
    ) -> ImportOutcome:
        """@import 한 줄을 CLAUDE.md 끝에 추가한다(멱등).

        import_permission_granted 동의 레코드(subject=CLAUDE.md 경로)가 전달될
        때만 쓴다. 그 외 어떤 경우에도 사용자 파일 바이트를 건드리지 않는다.
        """
        line = self.import_line()
        target = self.claude_md_path
        if not target.exists():
            return ImportOutcome(
                path=target, line=line, changed=False, reason=IMPORT_TARGET_MISSING
            )

        data = target.read_bytes()
        encoded = line.encode("utf-8")
        if encoded in data.split(b"\n"):
            return ImportOutcome(
                path=target, line=line, changed=False, reason=IMPORT_ALREADY_PRESENT
            )
        if permission is None:
            return ImportOutcome(
                path=target, line=line, changed=False, reason=IMPORT_NO_PERMISSION
            )
        if (
            not isinstance(permission, ConsentRecord)
            or permission.kind is not ConsentKind.IMPORT_PERMISSION_GRANTED
        ):
            logger.warning("import 허가가 아닌 레코드 거부: %r", permission)
            return ImportOutcome(
                path=target, line=line, changed=False, reason=IMPORT_INVALID_PERMISSION
            )
        subject = Path(permission.subject).expanduser().resolve()
        if subject != target:
            logger.warning(
                "import 허가 대상 불일치: 허가=%s, 대상=%s", subject, target
            )
            return ImportOutcome(
                path=target, line=line, changed=False, reason=IMPORT_SUBJECT_MISMATCH
            )

        separator = b"" if (not data or data.endswith(b"\n")) else b"\n"
        atomic_write_bytes(target, data + separator + encoded + b"\n")
        logger.info("CLAUDE.md @import 추가: %s", target)
        return ImportOutcome(path=target, line=line, changed=True, reason=IMPORT_ADDED)

    def ensure_import(self, permission: ConsentRecord | None = None) -> ImportOutcome:
        """CLAUDE.md 판독과 원자 교체를 대상 파일 잠금 안에서 수행한다."""
        with target_lock(self.claude_md_path):
            return self._ensure_import_unlocked(permission)

    def _remove_import_unlocked(self) -> ImportOutcome:
        """@import 한 줄 제거 - 전체 롤백 지점. 그 한 줄만 걷어낸다."""
        line = self.import_line()
        target = self.claude_md_path
        if not target.exists():
            return ImportOutcome(
                path=target, line=line, changed=False, reason=IMPORT_TARGET_MISSING
            )

        data = target.read_bytes()
        encoded = line.encode("utf-8")
        segments = data.split(b"\n")
        if encoded not in segments:
            return ImportOutcome(
                path=target, line=line, changed=False, reason=IMPORT_NOT_PRESENT
            )
        atomic_write_bytes(target, b"\n".join(seg for seg in segments if seg != encoded))
        logger.info("CLAUDE.md @import 제거(롤백): %s", target)
        return ImportOutcome(path=target, line=line, changed=True, reason=IMPORT_REMOVED)

    def remove_import(self) -> ImportOutcome:
        """CLAUDE.md 롤백을 대상 파일 잠금 안에서 원자 수행한다."""
        with target_lock(self.claude_md_path):
            return self._remove_import_unlocked()
