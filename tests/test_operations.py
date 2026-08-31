"""doctor, activation, export, backup의 실사용 운영 계약."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from popper.backup import BACKUP_MANIFEST, create_backup, inspect_backup
from popper.cli import _activation_state, main
from popper.doctor import run_doctor
from popper.exporter import EXPORT_FORMATS, render_export, write_export
from popper.store import EventStore
from popper.web.state import ColdOpenSession
from popper.writer import OwnedWriter


def _land(base: Path, session_id: str = "operations") -> EventStore:
    store = EventStore(base)
    session = ColdOpenSession(session_id=session_id, store=store, land_dir=base)
    for _ in range(session.snapshot().slots_total):
        session.strike("left")
    assert session.snapshot().landing.status == "landed"
    return store


def test_doctor_is_healthy_for_empty_writable_install(tmp_path: Path) -> None:
    report = run_doctor(tmp_path / "new-data")
    assert report.healthy
    assert {check.name for check in report.checks} >= {
        "python",
        "package_resources",
        "ground_truth_seal",
        "data_directory",
        "event_replay",
        "landed_outputs",
        "loopback_server",
    }


def test_doctor_reports_corrupt_event_stream_without_repairing_it(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    broken = sessions / "broken.jsonl"
    body = '{"type":"session_start"}\nnot-json\n'
    broken.write_text(body, encoding="utf-8")

    report = run_doctor(tmp_path)

    assert not report.healthy
    replay = next(check for check in report.checks if check.name == "event_replay")
    assert replay.status == "error"
    assert "JSONL" in replay.evidence
    assert broken.read_text(encoding="utf-8") == body


def test_activation_truth_distinguishes_inactive_active_and_drift(
    tmp_path: Path, monkeypatch
) -> None:
    home = tmp_path / "home"
    claude = home / ".claude"
    claude.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    base = tmp_path / "data"
    base.mkdir()
    (base / "POPPER.md").write_text("# rules\n", encoding="utf-8")
    writer = OwnedWriter(base_dir=base)
    claude_md = claude / "CLAUDE.md"
    claude_md.write_text("# User\n", encoding="utf-8")

    assert _activation_state(base)["status"] == "inactive"
    claude_md.write_text(f"# User\n{writer.import_line()}\n", encoding="utf-8")
    assert _activation_state(base)["status"] == "active"
    claude_md.write_text("# User\n@/old/popper/POPPER.md\n", encoding="utf-8")
    assert _activation_state(base)["status"] == "import-drift"


def test_all_export_formats_are_deterministic_and_explicit(tmp_path: Path) -> None:
    store = _land(tmp_path / "data")
    events = store.load_completed()
    rendered = {format_name: render_export(events, format_name) for format_name in EXPORT_FORMATS}

    assert rendered["markdown"].startswith("# Popper Rules")
    assert rendered["agents"].startswith("# Agent Instructions")
    assert rendered["claude"].startswith("# Claude Instructions")
    assert json.loads(rendered["json"])["artifact"] == "popper_rules_export"
    target = write_export(tmp_path / "AGENTS.md", rendered["agents"])
    assert target.read_text(encoding="utf-8") == rendered["agents"]


def test_backup_round_trip_inspection_and_tamper_detection(tmp_path: Path) -> None:
    base = tmp_path / "data"
    _land(base)
    archive = tmp_path / "popper-backup.zip"
    result = create_backup(base, archive)

    assert result.path == archive
    assert result.checksum_path.is_file()
    healthy = inspect_backup(archive)
    assert healthy.healthy
    assert healthy.session_count == 1
    assert healthy.file_count > 3

    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename.endswith("POPPER.md"):
                data += b"tampered"
            target.writestr(info, data)
    broken = inspect_backup(tampered)
    assert not broken.healthy
    assert any("checksum mismatch" in error for error in broken.errors)


def test_cli_json_surfaces_are_machine_readable(tmp_path: Path, capsys) -> None:
    assert main(["doctor", "--base-dir", str(tmp_path), "--json"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["artifact"] == "popper_doctor"

    assert main(["sessions", "--base-dir", str(tmp_path), "--json"]) == 0
    sessions = json.loads(capsys.readouterr().out)
    assert sessions == {"artifact": "popper_sessions", "sessions": []}


def test_backup_manifest_is_not_listed_as_payload(tmp_path: Path) -> None:
    archive = tmp_path / "empty.zip"
    create_backup(tmp_path / "empty-data", archive)
    with zipfile.ZipFile(archive) as backup:
        manifest = json.loads(backup.read(BACKUP_MANIFEST))
    assert BACKUP_MANIFEST not in manifest["files"]
