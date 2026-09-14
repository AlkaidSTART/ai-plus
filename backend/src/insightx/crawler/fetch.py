"""Playwright-based capture of rendered DOM snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from playwright.async_api import (
    Browser,
    BrowserContext,
    Playwright,
    async_playwright,
)

from insightx.crawler.dom import (
    DOM_SERIALIZER_SCRIPT,
    DomNode,
    validate_dom_node,
)


@dataclass(frozen=True, slots=True)
class FetchedPage:
    """Values captured from one browser navigation."""

    source_url: str
    final_url: str
    title: str
    http_status: int
    captured_at: datetime
    dom: DomNode


async def fetch_dom(
    url: str,
    *,
    timeout_ms: int,
    headless: bool,
) -> FetchedPage:
    """Open one URL with Chromium and capture its rendered DOM."""

    async with async_playwright() as playwright:
        return await fetch_with_playwright(
            playwright,
            url,
            timeout_ms=timeout_ms,
            headless=headless,
        )


async def fetch_with_playwright(
    playwright: Playwright,
    url: str,
    *,
    timeout_ms: int,
    headless: bool,
) -> FetchedPage:
    """Capture a page using an existing Playwright manager."""

    browser: Browser | None = None
    context: BrowserContext | None = None
    try:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
        if response is None:
            raise RuntimeError(f"navigation returned no response for {url}")

        dom_value = await page.evaluate(DOM_SERIALIZER_SCRIPT)
        if not isinstance(dom_value, dict):
            raise ValueError("DOM serializer did not return an element object")
        validate_dom_node(dom_value)

        title = await page.title()
        fetched = FetchedPage(
            source_url=url,
            final_url=page.url,
            title=title,
            http_status=response.status,
            captured_at=datetime.now(UTC),
            dom=cast(DomNode, dom_value),
        )
    except BaseException:
        try:
            await _close_browser_resources(context, browser)
        except BaseException:
            pass
        raise

    await _close_browser_resources(context, browser)
    return fetched


async def _close_browser_resources(
    context: BrowserContext | None,
    browser: Browser | None,
) -> None:
    """Close browser resources without masking the first cleanup failure."""

    first_error: BaseException | None = None
    if context is not None:
        try:
            await context.close()
        except BaseException as exc:
            first_error = exc
    if browser is not None:
        try:
            await browser.close()
        except BaseException as exc:
            if first_error is None:
                first_error = exc
    if first_error is not None:
        raise first_error
