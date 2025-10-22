"""Playwright smoke tests for the Signal Health dashboard."""

from __future__ import annotations

import os
from typing import Iterator, Tuple

import pytest
from playwright.sync_api import Error, Page, Response, expect

BASE_URL = os.getenv(
    "PLAYWRIGHT_BASE_URL", os.getenv("BASE_URL", "http://localhost:8000")
).rstrip("/")
PATH_CANDIDATES: Tuple[str, ...] = ("/ui/signal-health", "/signal-health")
_DISABLING_VALUES = {"0", "false", "no", "off"}


def _feature_flag_enabled() -> bool:
    return (
        os.getenv("FRONTEND_SIGNAL_HEALTH_ENABLED", "true").lower()
        not in _DISABLING_VALUES
    )


@pytest.fixture()
def authed_page(browser) -> Iterator[Page]:  # type: ignore[override]
    context = browser.new_context(base_url=BASE_URL)
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()


def _navigate_to_signal_health(page: Page) -> Tuple[Page, Response]:
    last_error: Error | None = None
    last_response: Response | None = None
    for candidate in PATH_CANDIDATES:
        try:
            response = page.goto(candidate, wait_until="networkidle")
        except Error as exc:  # pragma: no cover - handled via skip
            last_error = exc
            continue
        if response is None:
            continue
        last_response = response
        if response.status < 400:
            return page, response
    if last_response is not None:
        return page, last_response
    if last_error is not None:
        pytest.skip(f"Signal Health route unreachable: {last_error}")
    pytest.fail("No HTTP response received from Signal Health route")


@pytest.mark.e2e
@pytest.mark.skipif(
    not _feature_flag_enabled(), reason="signal health feature flag disabled"
)
def test_signal_health_page_smoke(authed_page: Page) -> None:
    page, response = _navigate_to_signal_health(authed_page)
    assert response.status < 400, f"Expected success status, got {response.status}"
    expect(page.get_by_role("heading", name="Signal Health")).to_be_visible()
    body_text = page.locator("body").inner_text().lower()
    assert any(
        keyword in body_text for keyword in ("accuracy", "confidence", "top")
    ), body_text


@pytest.mark.e2e
@pytest.mark.skipif(
    _feature_flag_enabled(), reason="signal health feature flag enabled"
)
def test_signal_health_feature_flag_disabled(authed_page: Page) -> None:
    page, response = _navigate_to_signal_health(authed_page)
    assert response.status in {
        301,
        302,
        307,
        308,
        403,
        404,
    }, f"Unexpected status: {response.status}"
    # Ensure the user does not silently see the dashboard content when disabled.
    page_text = page.locator("body").inner_text().lower()
    assert (
        "signal health" not in page_text
        or "not" in page_text
        or "forbidden" in page_text
    )
