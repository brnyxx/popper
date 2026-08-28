"""AC8 - 콜드 오픈 로컬 UI가 들고 있는 파생 상태.

질문/설정/온보딩 화면 없이 열려서 첫 페어를 즉시 띄운다. 첫 페어의 대비 축은
항상 자율성(COLD_OPEN_AXIS)이며, 픽스처 팩에서 렌더된 페어 목록을 결정론적으로
재배열해 얻는다.

사용자의 유일한 동사는 긋기다. 긋기가 들어오면 append-only 이벤트 로그에
StrikeEvent 하나가 쌓이고, 가설 카운터와 컴파일된 실행 룰은 그 스트림을 다시
접어서(fold) 파생한다. 카운터도 룰도 어디에도 저장되지 않는다 - 같은 스트림을
replay하면 항상 같은 값이 나온다.

런타임 LLM/네트워크 호출은 0회다. 픽스처 파일 읽기와 순수 함수 fold만 쓴다.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Sequence

from popper.compiler import CompiledRule, compile_rules
from popper.counter import fold
from popper.events import EventLog, Refutation, SchemaViolation, StrikeTarget
from popper.events import strike as make_strike
from popper.fixtures import (
    GENERIC_SKIN,
    RenderedPair,
    RenderedTranscript,
    RepoSkin,
    contrast_span,
    load_pack,
    refutation_for_fragment,
    render_all_pairs,
    scan_repo_skin,
)

logger = logging.getLogger(__name__)

#: 콜드 오픈이 반드시 첫 순서에 세우는 대비 축.
COLD_OPEN_AXIS = "autonomy"

#: 화면에 노출되는 축 이름 - UI 텍스트는 전부 한국어다.
AXIS_LABELS: dict[str, str] = {
    "response_language": "응답 언어",
    "verbosity": "장황함",
    "autonomy": "자율성",
    "commit_style": "커밋 스타일",
    "test_discipline": "테스트 규율",
    "comment_doc": "주석과 문서화",
    "error_behavior": "에러가 났을 때의 행동",
    "scope_adherence": "범위 준수",
}

#: 화면이 제공하는 유일한 입력 어포던스 - 긋기 대상 네 가지.
STRIKE_TARGETS: tuple[str, ...] = tuple(target.value for target in StrikeTarget)

#: 긋기 대상별 한국어 라벨.
STRIKE_LABELS: dict[str, str] = {
    StrikeTarget.LEFT.value: "왼쪽 긋기",
    StrikeTarget.RIGHT.value: "오른쪽 긋기",
    StrikeTarget.BOTH.value: "양쪽 모두 긋기",
    StrikeTarget.PAIR.value: "이 페어 통째로 긋기",
}


def axis_label(axis: str) -> str:
    """축의 한국어 라벨 - 미등록 축은 원문 그대로 돌려준다."""
    return AXIS_LABELS.get(axis, axis)


@dataclass(frozen=True, slots=True)
class PairView:
    """화면에 걸린 대비 페어 한 쌍 - 렌더된 좌우 본문과 귀속 정보."""

    pair_id: str
    scene_id: str
    axis: str
    axis_label: str
    left_value: str
    right_value: str
    left_text: str
    right_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "scene_id": self.scene_id,
            "axis": self.axis,
            "axis_label": self.axis_label,
            "left_value": self.left_value,
            "right_value": self.right_value,
            "left_text": self.left_text,
            "right_text": self.right_text,
        }


@dataclass(frozen=True, slots=True)
class RuleView:
    """컴파일 페인에 뿌려지는 실행 룰 한 줄."""

    axis: str
    axis_label: str
    value: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis": self.axis,
            "axis_label": self.axis_label,
            "value": self.value,
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class Snapshot:
    """한 시점의 화면 상태 - 전부 이벤트 스트림에서 파생된 값이다."""

    session_id: str
    pair: PairView
    remaining_combinations: int
    eliminated_pairs: int
    strike_count: int
    rules: tuple[RuleView, ...]
    last_strike: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "pair": self.pair.to_dict(),
            "remaining_combinations": self.remaining_combinations,
            "eliminated_pairs": self.eliminated_pairs,
            "strike_count": self.strike_count,
            "rules": [rule.to_dict() for rule in self.rules],
            "last_strike": self.last_strike,
            "strike_targets": list(STRIKE_TARGETS),
        }


def ordered_pairs(pairs: Sequence[RenderedPair]) -> tuple[RenderedPair, ...]:
    """콜드 오픈 축의 페어가 항상 앞에 오도록 결정론적으로 재배열한다.

    안정 정렬이라 축 내부 순서와 나머지 축들의 상대 순서는 그대로 보존된다.
    """
    return tuple(
        sorted(pairs, key=lambda pair: 0 if pair.axis == COLD_OPEN_AXIS else 1)
    )


def _contrast_refutation(transcript: RenderedTranscript) -> Refutation:
    """대비 슬롯 span을 축으로 귀속시킨 반증 provenance 한 건."""
    return refutation_for_fragment(transcript, contrast_span(transcript).fragment_id)


class ColdOpenSession:
    """질문 0개로 열리는 세션 - 긋기만 받고 나머지는 전부 fold로 파생한다."""

    __slots__ = ("_pairs", "_log", "_cursor", "_lock", "_session_id", "_last")

    def __init__(
        self,
        repo_root: Path | str | None = None,
        fixtures_dir: Path | str | None = None,
        session_id: str | None = None,
    ) -> None:
        pack = load_pack(fixtures_dir)
        skin: RepoSkin = GENERIC_SKIN if repo_root is None else scan_repo_skin(repo_root)
        self._pairs = ordered_pairs(render_all_pairs(pack, skin))
        if not self._pairs:
            raise SchemaViolation("픽스처 팩에서 페어를 하나도 렌더하지 못했다")
        if self._pairs[0].axis != COLD_OPEN_AXIS:
            raise SchemaViolation(f"콜드 오픈 첫 페어의 축이 {COLD_OPEN_AXIS}가 아니다")
        self._log = EventLog()
        self._cursor = 0
        self._lock = RLock()
        self._session_id = session_id or uuid.uuid4().hex
        self._last: str | None = None
        logger.debug(
            "콜드 오픈 세션 준비 완료: session=%s 첫 축=%s 페어=%d개",
            self._session_id,
            self._pairs[0].axis,
            len(self._pairs),
        )

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def log(self) -> EventLog:
        """append-only 이벤트 로그 - 세션의 단일 진실원."""
        return self._log

    def snapshot(self) -> Snapshot:
        """지금 화면에 걸릴 상태를 이벤트 스트림에서 다시 파생한다."""
        with self._lock:
            return self._derive()

    def strike(self, target: str) -> Snapshot:
        """긋기 한 건을 스트림에 쌓고 갱신된 상태를 돌려준다."""
        resolved = self._resolve(target)
        with self._lock:
            pair = self._pairs[self._cursor]
            event = make_strike(
                session_id=self._session_id,
                pair_id=pair.pair_id,
                axis=pair.axis,
                scene_id=pair.scene_id,
                target=resolved,
                refutations=self._refutations(pair, resolved),
            )
            self._log.append(event)
            self._last = resolved.value
            self._cursor = (self._cursor + 1) % len(self._pairs)
            logger.debug(
                "긋기 적재: target=%s axis=%s pair=%s",
                resolved.value,
                pair.axis,
                pair.pair_id,
            )
            return self._derive()

    @staticmethod
    def _resolve(target: str) -> StrikeTarget:
        try:
            return StrikeTarget(target)
        except ValueError as e:
            raise SchemaViolation(f"허용되지 않은 긋기 대상: {target!r}") from e

    @staticmethod
    def _refutations(pair: RenderedPair, target: StrikeTarget) -> tuple[Refutation, ...]:
        """긋기 대상에 맞는 반증 provenance를 대비 슬롯에서 뽑는다."""
        if target is StrikeTarget.PAIR:
            # 페어 긋기는 축x장면 판별력-없음 이벤트라 반증을 남기지 않는다.
            return ()
        sides: list[RenderedTranscript] = []
        if target in (StrikeTarget.LEFT, StrikeTarget.BOTH):
            sides.append(pair.left)
        if target in (StrikeTarget.RIGHT, StrikeTarget.BOTH):
            sides.append(pair.right)
        return tuple(_contrast_refutation(side) for side in sides)

    def _derive(self) -> Snapshot:
        events = self._log.events
        counter = fold(events)
        rules = compile_rules(events)
        return Snapshot(
            session_id=self._session_id,
            pair=self._pair_view(self._pairs[self._cursor]),
            remaining_combinations=counter.remaining_combinations,
            eliminated_pairs=counter.eliminated_pairs,
            strike_count=len(self._log.strikes()),
            rules=tuple(_rule_view(rule) for rule in rules),
            last_strike=self._last,
        )

    @staticmethod
    def _pair_view(pair: RenderedPair) -> PairView:
        return PairView(
            pair_id=pair.pair_id,
            scene_id=pair.scene_id,
            axis=pair.axis,
            axis_label=axis_label(pair.axis),
            left_value=pair.left_value,
            right_value=pair.right_value,
            left_text=pair.left.text,
            right_text=pair.right.text,
        )


def _rule_view(rule: CompiledRule) -> RuleView:
    return RuleView(
        axis=rule.axis,
        axis_label=axis_label(rule.axis),
        value=rule.value,
        text=rule.text,
    )
