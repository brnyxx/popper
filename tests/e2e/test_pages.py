"""Real-browser contracts for the generated bilingual GitHub Pages artifact."""

from __future__ import annotations

import importlib.util
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE_URL = "https://pages.example.test/popper/"
REPOSITORY_URL = "https://github.com/example/popper"


def _builder():
    path = ROOT / "scripts" / "build_site.py"
    spec = importlib.util.spec_from_file_location("build_site_e2e", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return


@contextmanager
def _serve(directory: Path):
    handler = partial(_QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_pages_bilingual_proof_navigation_and_assets(page, tmp_path: Path) -> None:
    output = tmp_path / "pages"
    _builder().build(output, site_url=SITE_URL, repository_url=REPOSITORY_URL)
    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    with _serve(output) as url:
        page.goto(url, wait_until="load")

        assert page.title() == "Popper — local CLAUDE.md behavior compiler"
        assert page.locator("html").get_attribute("lang") == "en"
        assert (
            page.get_by_role(
                "heading", name="Cross out the agent behavior you never want again."
            ).count()
            == 1
        )
        assert page.locator("script").count() == 0
        assert (
            page.locator(".transcript del")
            .inner_text()
            .startswith("Before fixing pagination")
        )
        assert (
            page.get_by_text("6,561 (3⁸; 8 axes, 3 values each)", exact=True).count()
            == 1
        )
        assert (
            page.get_by_text("4,374 after one value is falsified", exact=True).count()
            == 1
        )
        assert (
            page.get_by_text(
                "Act first, run focused verification, then report the change and evidence.",
                exact=True,
            ).count()
            == 1
        )
        assert page.locator(".storyboard").count() == 1
        assert (
            page.locator(".story-next")
            .inner_text()
            .endswith("Fixed. Tests pass. Here is what changed.")
        )
        animation_timings = page.locator(".storyboard").evaluate(
            """element => element.getAnimations({ subtree: true }).map(animation => {
              const timing = animation.effect.getTiming();
              return { duration: timing.duration, iterations: timing.iterations };
            })"""
        )
        assert len(animation_timings) == 4
        assert all(
            timing == {"duration": 4800, "iterations": 1}
            for timing in animation_timings
        )

        page.keyboard.press("Tab")
        assert page.locator(".skip-link").evaluate(
            "element => document.activeElement === element"
        )
        focus_style = page.locator(".skip-link").evaluate(
            "element => ({ width: getComputedStyle(element).outlineWidth, style: getComputedStyle(element).outlineStyle })"
        )
        assert focus_style == {"width": "3px", "style": "solid"}
        page.get_by_role("link", name="See the before and after").click()
        assert page.url.endswith("#outcome")

        disclosure = page.locator(".demo-disclosure")
        disclosure.locator("summary").click()
        assert disclosure.get_attribute("open") is not None
        page.wait_for_function(
            "() => { const image = document.querySelector('.demo-disclosure img'); return image.complete && image.naturalWidth === 960; }"
        )

        page.get_by_role("link", name="KO").first.click()
        assert page.title() == "Popper — 로컬 CLAUDE.md 행동 컴파일러"
        assert page.locator("html").get_attribute("lang") == "ko"
        assert (
            page.get_by_role(
                "heading",
                name="다시는 보고 싶지 않은 에이전트 행동에 빨간 줄을 그으세요.",
            ).count()
            == 1
        )
        assert (
            page.get_by_role("link", name="KO").first.get_attribute("aria-current")
            == "page"
        )
        assert (
            page.locator('link[rel="stylesheet"]').get_attribute("href")
            == "../assets/site.css"
        )
        assert all(item.startswith(url) for item in requests)


def test_pages_mobile_dark_reduced_motion_has_no_overflow(page, tmp_path: Path) -> None:
    output = tmp_path / "pages"
    _builder().build(output, site_url=SITE_URL, repository_url=REPOSITORY_URL)
    page.set_viewport_size({"width": 390, "height": 844})
    page.emulate_media(color_scheme="dark", reduced_motion="reduce")
    with _serve(output) as url:
        page.goto(url, wait_until="load")

        dimensions = page.evaluate(
            "() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth })"
        )
        assert dimensions == {"viewport": 390, "document": 390}
        assert page.locator("body").evaluate(
            "element => getComputedStyle(element).backgroundColor === 'rgb(36, 33, 29)'"
        )
        assert page.locator("html").evaluate(
            "element => getComputedStyle(element).scrollBehavior === 'auto'"
        )
        assert page.locator(".story-next").evaluate(
            "element => getComputedStyle(element).opacity === '1'"
        )
        assert page.locator(".strike-line").evaluate(
            "element => getComputedStyle(element).transform === 'matrix(1, 0, 0, 1, 0, 0)'"
        )
        for link in page.locator("header a").all():
            assert link.evaluate(
                "element => Number.parseFloat(getComputedStyle(element).minHeight) >= 44"
            )
