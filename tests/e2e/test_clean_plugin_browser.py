"""Install the plugin in an isolated Claude home, then exercise its cache."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from .test_browser import _finish_with_keyboard, _start_server, _strike_until


def test_clean_plugin_browser(page, tmp_path: Path) -> None:
    claude = shutil.which("claude")
    if claude is None:
        if os.environ.get("RUN_CLEAN_PLUGIN_E2E") == "1":
            pytest.fail("claude CLI is required when RUN_CLEAN_PLUGIN_E2E=1")
        pytest.skip("claude CLI is not installed")

    home = tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "HOME": str(home)}
    env.pop("CLAUDE_CONFIG_DIR", None)
    repo = Path(__file__).resolve().parents[2]
    marketplace = "popper-marketplace"
    plugin_id = "popper@popper-marketplace"
    subprocess.run(
        [claude, "plugin", "marketplace", "add", str(repo), "--scope", "user"],
        env=env,
        check=True,
        cwd=repo,
    )
    subprocess.run(
        [claude, "plugin", "install", plugin_id, "--scope", "user", "--yes"],
        env=env,
        check=True,
        cwd=repo,
    )
    listed = subprocess.run(
        [claude, "plugin", "list", "--json"],
        env=env,
        check=True,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    installed = json.loads(listed.stdout)
    assert plugin_id in json.dumps(installed)
    plugin_version = json.loads(
        (repo / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )["version"]
    cache = home / ".claude" / "plugins" / "cache"
    candidates = [
        p
        for p in cache.rglob("*")
        if p.is_dir()
        and p.name == plugin_version
        and marketplace in p.parts
        and "popper" in p.parts
    ]
    assert candidates, f"plugin cache version not found under {cache}"

    project = tmp_path / "project"
    project.mkdir()
    (project / "package.json").write_text('{"name":"fixture"}\n', encoding="utf-8")
    (project / "index.ts").write_text("export const ready = true;\n", encoding="utf-8")
    launcher = candidates[0] / "scripts" / "popper_plugin.py"
    assert launcher.is_file()
    landed = tmp_path / "landed"
    doctor = subprocess.run(
        [
            sys.executable,
            str(launcher),
            "doctor",
            "--base-dir",
            str(landed),
            "--json",
        ],
        cwd=project,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(doctor.stdout)["healthy"] is True

    first, url = _start_server(
        landed,
        cwd=project,
        env=env,
        command=[sys.executable, str(launcher)],
        extra_args=["--repo", str(project)],
    )
    second: subprocess.Popen[str] | None = None
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.locator('[data-strike-target="left"]').wait_for(state="visible")
        assert "Node.js" in page.locator("#left-text").inner_text()
        _strike_until(page, 4)
        first.terminate()
        first.wait(timeout=5)

        second, resumed_url = _start_server(
            landed,
            cwd=project,
            env=env,
            command=[sys.executable, str(launcher)],
            extra_args=["--repo", str(project)],
            operation="resume",
        )
        page.goto(resumed_url, wait_until="domcontentloaded")
        assert (
            page.get_by_role("progressbar", name="세션 슬롯 진행").get_attribute(
                "aria-valuenow"
            )
            == "4"
        )
        assert "Node.js" in page.locator("#left-text").inner_text()
        _finish_with_keyboard(page)
        assert page.locator("#stage-complete").evaluate(
            "element => document.activeElement === element"
        )
        assert "산출물이 착지했다" in page.locator("#landing").inner_text()
        assert second.wait(timeout=5) == 0
    finally:
        if first.poll() is None:
            first.kill()
        first.wait(timeout=5)
        if second is not None:
            if second.poll() is None:
                second.kill()
            second.wait(timeout=5)
