"""Browser-level coverage of the product cold-open flow."""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

URL_RE = re.compile(r"(https?://127\.0\.0\.1:\d+/)")


def _start_server(
    base_dir: Path, *, cwd: Path | None = None, env: dict[str, str] | None = None
) -> tuple[subprocess.Popen[str], str]:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "popper",
            "open",
            "--no-browser",
            "--base-dir",
            str(base_dir),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=cwd,
        env=env,
    )
    assert process.stderr is not None
    deadline = time.monotonic() + 15
    lines: list[str] = []
    while time.monotonic() < deadline:
        line = process.stderr.readline()
        if line:
            lines.append(line)
            match = URL_RE.search(line)
            if match:
                return process, match.group(1)
        elif process.poll() is not None:
            break
    process.kill()
    process.wait(timeout=5)
    raise AssertionError("server URL was not logged: " + "".join(lines))


def _finish_with_keyboard(page) -> None:
    target = page.locator('[data-strike-target="left"]').first
    page.keyboard.press("Tab")
    assert target.evaluate("element => document.activeElement === element")
    for _ in range(15):
        expected = (
            int(page.locator('[role="progressbar"]').get_attribute("aria-valuenow")) + 1
        )
        target.press("Enter")
        page.wait_for_function(
            """expected => Number(document.querySelector('[role=progressbar]')
            .getAttribute('aria-valuenow')) >= expected""",
            arg=expected,
        )
    page.locator("#stage-complete").wait_for(state="visible")


def test_product_browser_cold_open(page, tmp_path: Path) -> None:
    process, url = _start_server(tmp_path)
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.locator('[data-strike-target="left"]').wait_for(state="visible")
        assert page.get_by_role("button", name="왼쪽 긋기").count() == 1
        assert page.get_by_role("button", name="오른쪽 긋기").count() == 1
        assert page.get_by_role("progressbar", name="세션 슬롯 진행").count() == 1
        _finish_with_keyboard(page)
        assert "산출물이 착지했다" in page.locator("#landing").inner_text()
        assert list(tmp_path.glob("manifest*.json"))
        status = page.locator("#strike-status")
        assert status.get_attribute("role") == "status"
        assert status.get_attribute("aria-live") == "polite"
        assert status.text_content()
        assert process.wait(timeout=5) == 0
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
