"""popper CLI - /popper 스킬과 터미널이 쓰는 단일 진입점.

세션 런타임(popper.web)은 시각을 조회하지 않는다. 벽시계 읽기(재심 배너 판정),
브라우저 열기, 동의 원장 적재 같은 바깥세상 접점은 전부 이 경계에서 끝낸다.

명령:
  open         일반(product) 세션 - 콜드 오픈 서버를 열고 15긋기 완주 시 착지
  validate     검증(validation) 세션 - 판별 13 + 미러 프로브 2, 착지 없음
  recheck      4막 경량 재심 - manifest 재심 큐 선두를 5-7긋기로 재시험
  status       manifest/재심 배너/자기반증 판정 fold 요약
  land         저장된 이벤트 스트림에서 산출물 재착지 (수기 편집 감지 시 차단)
  enable       CLAUDE.md @import 한 줄 추가 - --grant 허가 레코드 필수
  rollback     @import 한 줄 제거 - 전체 롤백 지점
  optin        수기 룰 하나를 반증 대상으로 opt-in (default-in 금지)
  acknowledge  refutation_condition_met에 대한 인간 확정 이벤트 기록
"""

from __future__ import annotations

import argparse
import json
import logging
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from popper.compiler import (
    MANIFEST_JSON,
    CompiledRule as CompilerRule,
    HashMismatch,
    compile_rules,
    default_base_dir,
    write_outputs,
)
from popper.conflict import (
    CompiledRule as ConflictRule,
    ConsentKind,
    ConsentLedger,
    ConsentRecord,
    ConsentViolation,
    ManualRule,
    detect_conflicts,
)
from popper.events import Event, EventType
from popper.judgment import acknowledge, emit_condition_met, fold_judgment
from popper.recheck import (
    DEFAULT_BUDGET,
    MANUAL_COMMAND,
    RecheckViolation,
    check_due,
)
from popper.session import DEFAULT_PREREG_PATH, PROFILE_PRODUCT, PROFILE_VALIDATION
from popper.store import EventStore, StoreViolation
from popper.web.server import EPHEMERAL_PORT, HOST, build_server
from popper.web.state import PROFILE_RECHECK, ColdOpenSession
from popper.writer import OwnedWriter

logger = logging.getLogger("popper")

CONSENT_FILE = "consent.jsonl"
MANUAL_RULES_FILE = "manual_rules.json"
JUDGMENT_SESSION_ID = "judgment-ledger"


# ------------------------------------------------------------------ 파일 경계


def _load_manifest(base_dir: Path) -> dict[str, Any] | None:
    path = base_dir / MANIFEST_JSON
    if not path.exists():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("manifest를 읽지 못했다: %s", path)
        return None
    return document if isinstance(document, dict) else None


def _banner_text(manifest: Mapping[str, Any] | None) -> str | None:
    """재심 배너 - 벽시계는 여기(CLI 경계)에서만 읽는다."""
    if manifest is None:
        return None
    banner = check_due(manifest, datetime.now(timezone.utc))
    if banner.text is None:
        return None
    return f"{banner.text} - {MANUAL_COMMAND}로 재심에 들어갈 수 있다"


def _load_consent(base_dir: Path) -> ConsentLedger:
    path = base_dir / CONSENT_FILE
    ledger = ConsentLedger()
    if not path.exists():
        return ledger
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        logger.exception("동의 원장을 읽지 못했다: %s", path)
        return ledger
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            fields: dict[str, Any] = {
                "kind": ConsentKind(str(record.get("kind"))),
                "subject": str(record.get("subject", "")),
            }
            if record.get("record_id"):
                fields["record_id"] = str(record["record_id"])
            if record.get("at"):
                fields["at"] = str(record["at"])
            ledger.append(ConsentRecord(**fields))
        except (json.JSONDecodeError, ValueError, ConsentViolation, TypeError) as exc:
            logger.warning("동의 원장 손상 - %s:%d (%s), 해당 줄을 무시한다", path, number, exc)
    return ledger


def _persist_consent(base_dir: Path, record: ConsentRecord) -> None:
    path = base_dir / CONSENT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def _load_manual_rules(base_dir: Path) -> tuple[ManualRule, ...]:
    path = base_dir / MANUAL_RULES_FILE
    if not path.exists():
        return ()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("수기 룰 파일을 읽지 못했다: %s", path)
        return ()
    rules: list[ManualRule] = []
    for entry in document.get("rules", ()):
        if not isinstance(entry, Mapping):
            continue
        rules.append(
            ManualRule(
                rule_id=str(entry.get("rule_id", "")),
                axis=str(entry.get("axis", "")),
                value=str(entry.get("value", "")),
                text=str(entry.get("text", "")),
                source_path=entry.get("source_path"),
            )
        )
    return tuple(rules)


def _conflict_rule(rule: CompilerRule) -> ConflictRule:
    return ConflictRule(
        rule_id=rule.rule_id,
        axis=rule.axis,
        value=rule.value,
        text=rule.text,
        corroboration_grade=rule.corroboration_grade,
        value_source=rule.value_source,
        strike_provenance=tuple(rule.provenance),
    )


def _conflicts_for(
    base_dir: Path,
) -> Callable[[tuple[CompilerRule, ...]], Sequence[Mapping[str, Any]]]:
    """착지 시점 충돌 탐지 - opt-in 수기 룰만 반증 대상으로 본다(AC6)."""

    def compute(rules: tuple[CompilerRule, ...]) -> Sequence[Mapping[str, Any]]:
        manual = _load_manual_rules(base_dir)
        if not manual:
            return ()
        consent = _load_consent(base_dir)
        report = detect_conflicts(
            manual,
            tuple(_conflict_rule(rule) for rule in rules),
            catalog_version="v1",
            consent=consent,
        )
        return report.report_rows()

    return compute


def _seal_payload() -> dict[str, Any] | None:
    """봉인 문서에서 판정 기준 payload를 파생한다 - 수치의 소유자는 그 문서다.

    금지 어휘(code_scan_guard)가 런타임에 존재하면 안 되므로 동결 항목은
    키 이름이 아니라 unit으로 식별한다: 검증 세션 수는 unit=="sessions",
    누적 판별 인스턴스는 unit이 "instances"로 시작하는 유일 항목이다.
    """
    try:
        document = json.loads(DEFAULT_PREREG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("봉인 문서를 읽지 못했다: %s", DEFAULT_PREREG_PATH)
        return None
    seal = document.get("seal", {})
    body = document.get("document", {})
    frozen = body.get("frozen_parameters", {})

    def by_unit(matcher: Callable[[str], bool]) -> int | None:
        values = [
            entry.get("value")
            for entry in frozen.values()
            if isinstance(entry, Mapping) and matcher(str(entry.get("unit", "")))
        ]
        if len(values) == 1 and isinstance(values[0], int):
            return values[0]
        return None

    sessions_needed = by_unit(lambda unit: unit == "sessions")
    instances_needed = by_unit(lambda unit: unit.startswith("instances"))
    if sessions_needed is None or instances_needed is None:
        logger.error("봉인 문서에서 판정 기준을 식별하지 못했다")
        return None
    return {
        "catalog_version": str(body.get("catalog_version", "v1")),
        "digest": str(seal.get("digest", "")),
        "required_valid_sessions": sessions_needed,
        "required_discriminative_instances": instances_needed,
    }


def _ensure_seal_event(store: EventStore) -> None:
    """검증 세션 이전에 prereg_sealed 이벤트가 스트림에 정확히 하나 있게 한다."""
    for event in store.load_all():
        if getattr(event, "type", None) is EventType.PREREG_SEALED:
            return
    payload = _seal_payload()
    if payload is None:
        return
    store.append(
        Event(type=EventType.PREREG_SEALED, session_id="prereg", payload=payload)
    )
    logger.info("봉인 기준 적재: prereg_sealed (digest=%s...)", payload["digest"][:12])


def _validation_gap_hours() -> float | None:
    """봉인 문서가 소유하는 검증 세션 간 최소 간격을 읽는다."""
    try:
        document = json.loads(DEFAULT_PREREG_PATH.read_text(encoding="utf-8"))
        threats = document["document"]["threats_to_validity"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        logger.exception("봉인 문서에서 검증 세션 간격을 읽지 못했다")
        return None
    entries = threats.values() if isinstance(threats, Mapping) else threats
    values = [
        entry.get("inter_session_gap_hours_min")
        for entry in entries
        if isinstance(entry, Mapping)
        and isinstance(entry.get("inter_session_gap_hours_min"), (int, float))
    ]
    if len(values) != 1 or values[0] <= 0:
        logger.error("봉인 문서의 검증 세션 간격 기준이 유일하지 않다")
        return None
    return float(values[0])


def _latest_validation_end(
    events: Sequence[Event | Any],
) -> datetime | None:
    validation_sessions = {
        event.session_id
        for event in events
        if isinstance(event, Event)
        and event.type is EventType.SESSION_START
        and event.payload.get("profile") == PROFILE_VALIDATION
    }
    ended: list[datetime] = []
    for event in events:
        if (
            not isinstance(event, Event)
            or event.type
            not in (EventType.SESSION_VALIDATED, EventType.SESSION_VOIDED)
        ):
            continue
        if (
            event.payload.get("profile") != PROFILE_VALIDATION
            and event.session_id not in validation_sessions
        ):
            continue
        try:
            ended.append(datetime.fromisoformat(event.at))
        except ValueError:
            logger.warning("검증 종료 시각을 해석하지 못했다: %s", event.event_id)
    return max(ended) if ended else None


# ---------------------------------------------------------------- 서브 명령


def _serve(session: ColdOpenSession, args: argparse.Namespace) -> int:
    server = build_server(session=session, host=args.host, port=args.port)
    logger.info("긋기 화면: %s", server.url)
    logger.info("세션: %s (%s) - 중단은 Ctrl+C", session.session_id, session.profile)
    if not args.no_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("서버를 닫는다")
    finally:
        server.shutdown()
        server.server_close()
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    base = Path(args.base_dir)
    manifest = _load_manifest(base)
    store = EventStore(base)
    session = ColdOpenSession(
        repo_root=args.repo,
        profile=PROFILE_PRODUCT,
        store=store,
        land_dir=base,
        history=store.load_all(),
        banner=_banner_text(manifest),
        conflicts_for=_conflicts_for(base),
    )
    return _serve(session, args)


def cmd_validate(args: argparse.Namespace) -> int:
    base = Path(args.base_dir)
    store = EventStore(base)
    _ensure_seal_event(store)
    history = store.load_all()
    gap_hours = _validation_gap_hours()
    if gap_hours is None:
        return 1
    previous = _latest_validation_end(history)
    now = datetime.now(timezone.utc)
    if previous is not None and (now - previous).total_seconds() < gap_hours * 3600:
        logger.error(
            "검증 세션 간 봉인 간격이 지나지 않았다 - 마지막 종료 %s",
            previous.isoformat(),
        )
        return 1
    session = ColdOpenSession(
        repo_root=args.repo,
        profile=PROFILE_VALIDATION,
        store=store,
        land_dir=base,
        history=history,
    )
    return _serve(session, args)


def cmd_recheck(args: argparse.Namespace) -> int:
    base = Path(args.base_dir)
    manifest = _load_manifest(base)
    if manifest is None:
        logger.error("착지된 manifest가 없다 - 일반 세션(popper open)을 먼저 완주해라")
        return 1
    queue = manifest.get("recheck_queue")
    if (
        not isinstance(queue, Sequence)
        or isinstance(queue, (str, bytes))
        or not queue
    ):
        logger.info("재심 대기 0건 - 열 재심 세션이 없다")
        return 0
    store = EventStore(base)
    try:
        session = ColdOpenSession(
            repo_root=args.repo,
            profile=PROFILE_RECHECK,
            store=store,
            land_dir=base,
            history=store.load_all(),
            recheck_manifest=manifest,
            recheck_budget=args.budget,
            conflicts_for=_conflicts_for(base),
        )
    except RecheckViolation as exc:
        logger.error("%s", exc)
        return 1
    return _serve(session, args)


def cmd_status(args: argparse.Namespace) -> int:
    base = Path(args.base_dir)
    manifest = _load_manifest(base)
    if manifest is None:
        logger.info("착지된 산출물이 없다 - popper open으로 첫 세션을 완주해라")
    else:
        logger.info("착지 디렉토리: %s", base)
        logger.info("마지막 착지: %s", manifest.get("generated_at"))
        logger.info("마지막 재심: %s", manifest.get("last_review"))
        logger.info("남은 가설 조합: %s", manifest.get("remaining_combinations"))
        queue = manifest.get("recheck_queue") or ()
        logger.info("재심 대기: %d건", len(queue))
        banner = _banner_text(manifest)
        if banner:
            logger.info("배너: %s", banner)

    store = EventStore(base)
    events = store.load_all()
    logger.info("저장된 세션: %d개, 이벤트 %d건", len(store.session_ids()), len(events))
    state = fold_judgment(events)
    logger.info(
        "자기반증 판정: 유효 검증 세션 %d, 판별 인스턴스 %d, 정복원 %d, 오복원 %d",
        state.valid_sessions,
        state.discriminative_instances,
        state.correct_restorations,
        state.mis_restorations,
    )
    if state.core_refutation_confirmed:
        logger.info("핵심 반증 확정 - 긋기-only 접근이 반증됐다 (직접편집 전환 피벗)")
    elif state.condition_met:
        logger.info(
            "refutation_condition_met 성립 - 확정은 popper acknowledge --actor <이름>"
        )
    return 0


def cmd_land(args: argparse.Namespace) -> int:
    base = Path(args.base_dir)
    store = EventStore(base)
    events = store.load_all()
    if not events:
        logger.error("저장된 이벤트가 없다 - 착지할 스트림이 없다")
        return 1
    try:
        manifest = _load_manifest(base) or {}
        result = write_outputs(
            events,
            base_dir=base,
            session_id=manifest.get("session_id"),
            acknowledge_mismatch=args.acknowledge_mismatch,
            conflicts=_conflicts_for(base)(compile_rules(events)),
        )
    except HashMismatch as e:
        logger.error("착지 차단 - content hash 불일치 (silent overwrite 금지)")
        for record in e.records:
            logger.error("  %s (%s)", record.get("path"), record.get("reason"))
        logger.error("의도한 재착지라면 --acknowledge-mismatch를 붙여라")
        return 1
    logger.info("착지 완료: %s", result.base_dir)
    for path in result.written:
        logger.info("  %s", path)
    return 0


def cmd_enable(args: argparse.Namespace) -> int:
    base = Path(args.base_dir)
    writer = OwnedWriter(base_dir=base)
    if not args.grant:
        logger.info("추가될 한 줄: %s", writer.import_line())
        logger.info("사용자 파일은 허가 없이는 건드리지 않는다 - --grant로 허가를 명시해라")
        return 1
    record = ConsentRecord(
        kind=ConsentKind.IMPORT_PERMISSION_GRANTED,
        subject=str(writer.claude_md_path),
    )
    _persist_consent(base, record)
    outcome = writer.ensure_import(record)
    logger.info("결과: %s (%s)", outcome.reason, outcome.path)
    return 0 if outcome.reason in ("added", "already_present") else 1


def cmd_rollback(args: argparse.Namespace) -> int:
    writer = OwnedWriter(base_dir=Path(args.base_dir))
    outcome = writer.remove_import()
    logger.info("결과: %s (%s)", outcome.reason, outcome.path)
    return 0 if outcome.reason in ("removed", "not_present") else 1


def cmd_optin(args: argparse.Namespace) -> int:
    base = Path(args.base_dir)
    record = ConsentRecord(kind=ConsentKind.MANUAL_RULE_OPTED_IN, subject=args.rule_id)
    _persist_consent(base, record)
    logger.info("수기 룰 opt-in 기록: %s", args.rule_id)
    return 0


def cmd_acknowledge(args: argparse.Namespace) -> int:
    base = Path(args.base_dir)
    store = EventStore(base)
    state = fold_judgment(store.load_all())
    if not state.condition_met:
        logger.error("refutation_condition_met 미성립 - 인간 확정은 조건 성립 후에만 가능하다")
        return 1
    condition = emit_condition_met(state, JUDGMENT_SESSION_ID)
    if condition is not None and not state.supported_condition_events:
        store.append(condition)
        logger.info("기계 방출 기록: refutation_condition_met")
    store.append(acknowledge(JUDGMENT_SESSION_ID, args.actor))
    logger.info("인간 확정 기록: refutation_acknowledged (actor=%s)", args.actor)
    logger.info("핵심 반증 확정 - 긋기-only 접근을 직접편집 전환으로 피벗한다")
    return 0


# ------------------------------------------------------------------- 파서


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--base-dir",
        default=str(default_base_dir()),
        help="popper 소유 디렉토리 (기본 ~/.claude/popper)",
    )


def _add_serve_common(parser: argparse.ArgumentParser) -> None:
    _add_common(parser)
    parser.add_argument("--host", default=HOST, help="바인딩할 주소")
    parser.add_argument("--port", type=int, default=EPHEMERAL_PORT, help="바인딩할 포트")
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="슬롯 치환에 쓸 대상 레포 경로. 생략하면 일반 skin을 쓴다",
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="브라우저를 자동으로 열지 않는다"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="popper",
        description="반증(긋기)만으로 Claude Code 설정을 수렴시키는 도구",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_open = sub.add_parser("open", help="일반 세션을 연다 (15긋기, 완주 시 착지)")
    _add_serve_common(p_open)
    p_open.set_defaults(func=cmd_open)

    p_validate = sub.add_parser(
        "validate", help="검증 세션을 연다 (판별 13 + 미러 프로브 2)"
    )
    _add_serve_common(p_validate)
    p_validate.set_defaults(func=cmd_validate)

    p_recheck = sub.add_parser("recheck", help="4막 경량 재심 세션을 연다 (5-7긋기)")
    _add_serve_common(p_recheck)
    p_recheck.add_argument(
        "--budget", type=int, default=DEFAULT_BUDGET, help="재심 긋기 예산 (5-7)"
    )
    p_recheck.set_defaults(func=cmd_recheck)

    p_status = sub.add_parser("status", help="착지/재심/자기반증 판정 요약")
    _add_common(p_status)
    p_status.set_defaults(func=cmd_status)

    p_land = sub.add_parser("land", help="저장된 스트림에서 산출물 재착지")
    _add_common(p_land)
    p_land.add_argument(
        "--acknowledge-mismatch",
        action="store_true",
        help="수기 편집 감지를 manifest에 기록하고 착지를 강행한다",
    )
    p_land.set_defaults(func=cmd_land)

    p_enable = sub.add_parser("enable", help="CLAUDE.md @import 한 줄 추가 (허가 필수)")
    _add_common(p_enable)
    p_enable.add_argument(
        "--grant", action="store_true", help="import_permission_granted 허가를 기록한다"
    )
    p_enable.set_defaults(func=cmd_enable)

    p_rollback = sub.add_parser("rollback", help="@import 한 줄 제거 (전체 롤백 지점)")
    _add_common(p_rollback)
    p_rollback.set_defaults(func=cmd_rollback)

    p_optin = sub.add_parser("optin", help="수기 룰 반증 대상 opt-in")
    _add_common(p_optin)
    p_optin.add_argument("rule_id", help="manual_rules.json의 rule_id")
    p_optin.set_defaults(func=cmd_optin)

    p_ack = sub.add_parser(
        "acknowledge", help="핵심 반증 인간 확정 (refutation_acknowledged)"
    )
    _add_common(p_ack)
    p_ack.add_argument("--actor", required=True, help="확정 주체 이름")
    p_ack.set_defaults(func=cmd_acknowledge)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except StoreViolation as exc:
        logger.error("이벤트 스토어 손상 - %s", exc)
        logger.error(
            "append-only 스트림은 자동 복구하지 않는다 - sessions/ 안 해당 파일의 손상 줄을 직접 확인해라"
        )
        return 1
