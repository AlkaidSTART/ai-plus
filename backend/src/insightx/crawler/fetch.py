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
    Page,
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

# ponytail: stealth — upgrade to playwright-stealth or browser-profile
#   rotation when Amazon starts detecting the init_script approach.
_STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = {runtime: {}};
"""

# JS snippet to scroll the Amazon review section into view and wait for
# lazy-loaded review cards to appear.  Returns the count of reviews found
# (0 means none loaded even after scrolling).
_SCROLL_TO_REVIEWS_SCRIPT = """
async () => {
    // Try to find the reviews widget and scroll to it
    const selectors = [
        '#cm-cr-dp-review-list',
        '[data-hook="reviews-medley-widget"]',
        '#reviewsMedley',
        '#customer-reviews-content',
    ];
    let target = null;
    for (const sel of selectors) {
        target = document.querySelector(sel);
        if (target) break;
    }
    if (target) {
        target.scrollIntoView({behavior: 'instant', block: 'center'});
    } else {
        // No review container found — scroll to bottom to trigger any
        // lazy-load and then back up.
        window.scrollTo(0, document.body.scrollHeight * 0.75);
    }

    // Wait up to 5s for at least one review card to appear
    const deadline = Date.now() + 5000;
    while (Date.now() < deadline) {
        const count = document.querySelectorAll('[data-hook="review"]').length;
        if (count > 0) return count;
        await new Promise(r => setTimeout(r, 300));
    }

    // Second attempt: click "See more reviews" link if present
    const seeMore = document.querySelector(
        '[data-hook="see-all-reviews-link-foot"], '
      + 'a[href*="product-reviews"], '
      + '.cr-widget-FocalReviews a.a-link-emphasis'
    );
    // Don't navigate — just trigger the lazy loader by scrolling again
    if (seeMore) {
        seeMore.scrollIntoView({behavior: 'instant', block: 'center'});
        await new Promise(r => setTimeout(r, 2000));
    }

    return document.querySelectorAll('[data-hook="review"]').length;
}
"""


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
    backoff and jitter.  Each attempt uses a fresh browser instance with
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


async def _create_stealth_context(
    browser: Browser,
) -> BrowserContext:
    """Create a browser context with randomised fingerprint and stealth patches."""

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
    await context.add_init_script(_STEALTH_INIT_SCRIPT)
    return context


async def _scroll_for_reviews(page: Page) -> int:
    """Scroll to the review section and return how many review cards loaded."""

    try:
        count = await page.evaluate(_SCROLL_TO_REVIEWS_SCRIPT)
        return int(count) if isinstance(count, (int, float)) else 0
    except Exception:
        logger.debug("Review-scroll script raised; continuing with current DOM")
        return 0


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
            "--no-first-run",
            "--no-default-browser-check",
        ]
        browser = await playwright.chromium.launch(
            headless=headless,
            args=launch_args,
        )
        context = await _create_stealth_context(browser)
        page = await context.new_page()

        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
        if response is None:
            raise RuntimeError(f"navigation returned no response for {url}")

        # Wait for full network idle — catches XHR-loaded review widgets
        try:
            await page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass  # best-effort; proceed with what we have

        # Scroll to review section and wait for lazy-loaded cards
        review_count = await _scroll_for_reviews(page)
        logger.info(
            "Scrolled to reviews for %s — found %d review card(s)", url, review_count
        )

        # Brief random pause for any remaining rendering
        await page.wait_for_timeout(random.randint(800, 1500))

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
