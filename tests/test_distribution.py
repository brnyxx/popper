"""GA 배포 메타데이터와 결정론적 플러그인 아카이브 계약."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_MANIFEST = ROOT / ".claude-plugin" / "marketplace.json"


def _archive_module():
    path = ROOT / "scripts" / "build_plugin_archive.py"
    spec = importlib.util.spec_from_file_location("build_plugin_archive", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_marketplace_and_package_versions_match() -> None:
    plugin = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    marketplace = json.loads(MARKETPLACE_MANIFEST.read_text(encoding="utf-8"))
    entry = marketplace["plugins"][0]

    assert marketplace["name"] == "popper-marketplace"
    assert entry["name"] == plugin["name"] == "popper"
    assert entry["version"] == plugin["version"] == "1.1.0"
    assert entry["source"] == "./"
    assert f'version = "{plugin["version"]}"' in (
        ROOT / "pyproject.toml"
    ).read_text(encoding="utf-8")


def test_plugin_archive_is_deterministic_and_self_contained(tmp_path: Path) -> None:
    module = _archive_module()
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    module.build_archive(ROOT, first)
    module.build_archive(ROOT, second)

    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(
        second.read_bytes()
    ).digest()
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        assert ".claude-plugin/plugin.json" in names
        assert "skills/popper/SKILL.md" in names
        assert "scripts/popper_plugin.py" in names
        assert "popper/_data/prereg/prereg_sealed.txt" in names
        assert "popper/_data/ground_truth/ground_truth.txt" in names
        assert "LICENSE" in names
        assert not any(name.startswith(("tests/", ".git/", "build/")) for name in names)
        assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)


def test_public_distribution_has_license_and_automation() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "Copyright (c) 2026 Brian Kim" in license_text
    assert (ROOT / ".github" / "workflows" / "ci.yml").is_file()
    assert (ROOT / ".github" / "workflows" / "release.yml").is_file()


def test_skill_distinguishes_servers_from_sync_diagnostics() -> None:
    skill = (ROOT / "skills" / "popper" / "SKILL.md").read_text(encoding="utf-8")
    assert "| (없음) 또는 `open` | 백그라운드+URL |" in skill
    assert "| `doctor` | 포그라운드 출력 |" in skill
    assert "조회·진단 명령(`status`, `sessions`, `doctor`)" in skill
