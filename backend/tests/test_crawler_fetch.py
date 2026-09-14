from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from insightx.crawler.dom import DOM_SERIALIZER_SCRIPT, DomNode
from insightx.crawler.fetch import fetch_with_playwright


def sample_dom() -> DomNode:
    return {
        "type": "element",
        "tag": "html",
        "attributes": {},
        "children": [{"type": "text", "text": "captured"}],
    }


def build_playwright(
    *,
    dom: object | None = None,
    response: object | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    page = MagicMock()
    page.url = "https://example.com/final"
    page.goto = AsyncMock(return_value=response)
    page.evaluate = AsyncMock(return_value=sample_dom() if dom is None else dom)
    page.title = AsyncMock(return_value="Captured page")

    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    context.close = AsyncMock()

    browser = MagicMock()
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()

    chromium = MagicMock()
    chromium.launch = AsyncMock(return_value=browser)

    playwright = MagicMock()
    playwright.chromium = chromium
    return playwright, chromium, browser, context


async def test_fetch_with_playwright_captures_rendered_values_and_closes() -> None:
    response = MagicMock(status=201)
    playwright, chromium, browser, context = build_playwright(response=response)

    fetched = await fetch_with_playwright(
        playwright,
        "https://example.com/start",
        timeout_ms=12_345,
        headless=False,
    )

    chromium.launch.assert_awaited_once_with(headless=False)
    browser.new_context.assert_awaited_once_with()
    context.new_page.assert_awaited_once_with()
    context.new_page.return_value.goto.assert_awaited_once_with(
        "https://example.com/start",
        wait_until="domcontentloaded",
        timeout=12_345,
    )
    context.new_page.return_value.evaluate.assert_awaited_once_with(
        DOM_SERIALIZER_SCRIPT
    )
    context.new_page.return_value.title.assert_awaited_once_with()
    assert fetched.source_url == "https://example.com/start"
    assert fetched.final_url == "https://example.com/final"
    assert fetched.title == "Captured page"
    assert fetched.http_status == 201
    assert fetched.dom == sample_dom()
    assert fetched.captured_at.tzinfo is UTC
    assert fetched.captured_at <= datetime.now(UTC)
    context.close.assert_awaited_once_with()
    browser.close.assert_awaited_once_with()


async def test_fetch_with_playwright_rejects_missing_navigation_response() -> None:
    playwright, _, browser, context = build_playwright(response=None)

    with pytest.raises(RuntimeError, match="navigation returned no response"):
        await fetch_with_playwright(
            playwright,
            "https://example.com/start",
            timeout_ms=1_000,
            headless=True,
        )

    context.close.assert_awaited_once_with()
    browser.close.assert_awaited_once_with()


async def test_fetch_with_playwright_rejects_invalid_serialized_dom() -> None:
    response = MagicMock(status=200)
    playwright, _, browser, context = build_playwright(
        dom={"type": "element", "tag": "DIV", "attributes": {}, "children": []},
        response=response,
    )

    with pytest.raises(ValueError, match="lowercase"):
        await fetch_with_playwright(
            playwright,
            "https://example.com/start",
            timeout_ms=1_000,
            headless=True,
        )

    context.close.assert_awaited_once_with()
    browser.close.assert_awaited_once_with()


async def test_fetch_preserves_navigation_error_when_cleanup_fails() -> None:
    playwright, _, browser, context = build_playwright()
    context.new_page.return_value.goto.side_effect = TimeoutError(
        "navigation timed out"
    )
    context.close.side_effect = RuntimeError("context close failed")
    browser.close.side_effect = RuntimeError("browser close failed")

    with pytest.raises(TimeoutError, match="navigation timed out"):
        await fetch_with_playwright(
            playwright,
            "https://example.com/start",
            timeout_ms=1_000,
            headless=True,
        )

    context.close.assert_awaited_once_with()
    browser.close.assert_awaited_once_with()


async def test_fetch_propagates_first_cleanup_failure_after_success() -> None:
    response = MagicMock(status=200)
    playwright, _, browser, context = build_playwright(response=response)
    context.close.side_effect = RuntimeError("context close failed")
    browser.close.side_effect = RuntimeError("browser close failed")

    with pytest.raises(RuntimeError, match="context close failed"):
        await fetch_with_playwright(
            playwright,
            "https://example.com/start",
            timeout_ms=1_000,
            headless=True,
        )

    context.close.assert_awaited_once_with()
    browser.close.assert_awaited_once_with()
