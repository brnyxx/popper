"""Playwright fixtures for loopback browser end-to-end tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def browser():
    playwright = pytest.importorskip("playwright.sync_api").sync_playwright().start()
    browser_name = os.environ.get("BROWSER", "chromium").lower()
    if browser_name not in {"chromium", "firefox", "webkit"}:
        playwright.stop()
        pytest.fail("BROWSER must be chromium, firefox, or webkit")
    try:
        instance = getattr(playwright, browser_name).launch(headless=True)
    except Exception as exc:
        playwright.stop()
        if os.environ.get("CI") or os.environ.get("REQUIRE_BROWSER_E2E") == "1":
            pytest.fail(f"Playwright {browser_name} launch failed: {exc}")
        pytest.skip(f"Playwright {browser_name} executable is unavailable: {exc}")
    yield instance
    instance.close()
    playwright.stop()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()
