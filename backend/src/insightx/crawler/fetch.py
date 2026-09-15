"""Playwright-based capture of rendered DOM snapshots."""

from __future__ import annotations

import asyncio
import logging
import random
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

logger = logging.getLogger(__name__)

# ---------- browser fingerprint presets ----------

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

_DEFAULT_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # seconds, exponential backoff


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
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> FetchedPage:
    """Open one URL with Chromium and capture its rendered DOM.

    Retries transient failures (connection reset, timeout) with exponential
    backoff and jitter. Each attempt uses a fresh browser instance with
    randomised fingerprint to reduce bot-detection risk.
    """

    last_error: BaseException | None = None
    for attempt in range(1, max_retries + 1):
        try:
            async with async_playwright() as playwright:
                return await fetch_with_playwright(
                    playwright,
                    url,
                    timeout_ms=timeout_ms,
                    headless=headless,
                )
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.warning(
                    "Fetch attempt %d/%d failed for %s: %s — retrying in %.1fs",
                    attempt,
                    max_retries,
                    url,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Fetch attempt %d/%d failed for %s: %s — no retries left",
                    attempt,
                    max_retries,
                    url,
                    exc,
                )
    raise last_error  # type: ignore[misc]


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
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
        ]
        browser = await playwright.chromium.launch(
            headless=headless,
            args=launch_args,
        )
        ua = random.choice(_USER_AGENTS)
        viewport = random.choice(_VIEWPORTS)
        context = await browser.new_context(
            user_agent=ua,
            viewport=viewport,
            locale="en-US",
            timezone_id="America/New_York",
            java_script_enabled=True,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Upgrade-Insecure-Requests": "1",
            },
        )

        # Remove navigator.webdriver flag that exposes automation
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
            """
        )

        page = await context.new_page()
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
        if response is None:
            raise RuntimeError(f"navigation returned no response for {url}")

        # Brief random pause to let lazy-loaded content settle
        await page.wait_for_timeout(random.randint(1500, 3000))

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
