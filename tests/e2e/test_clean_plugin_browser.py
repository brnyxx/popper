"""Install the plugin in an isolated Claude home, then exercise its cache."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from .test_browser import _finish_with_keyboard, _start_server


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
    cache = home / ".claude" / "plugins" / "cache"
    candidates = [
        p
        for p in cache.rglob("*")
        if p.is_dir() and p.name == "1.0.0" and marketplace in p.parts and "popper" in p.parts
    ]
    assert candidates, f"plugin cache version not found under {cache}"

    process, url = _start_server(
        tmp_path / "landed",
        cwd=candidates[0],
        env=env,
    )
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.locator('[data-strike-target="left"]').wait_for(state="visible")
        _finish_with_keyboard(page)
        assert "산출물이 착지했다" in page.locator("#landing").inner_text()
        assert process.wait(timeout=5) == 0
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
