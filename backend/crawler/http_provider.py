"""Configurable HTTP Amazon data provider.

Calls a configurable retail data gateway (`AMAZON_API_BASE_URL`), which is a
deployment-time decision (docs/04-技术方案 marks the earlier
`api.example-retail-gateway.com` as a placeholder that must never be used).
Implements timeout, retry with exponential backoff and simple rate limiting.
"""

import asyncio
import logging
import time

import httpx

from crawler.base import (
    AmazonFetchResult,
    ProductMetadata,
    UpstreamError,
    normalize_review,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
REQUEST_TIMEOUT = 15.0
MIN_REQUEST_INTERVAL = 0.2  # seconds between upstream calls (rate limit)


class ConfigurableHttpAmazonProvider:
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        max_reviews_per_request: int = 100,
        timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        if not base_url:
            raise UpstreamError(
                "AMAZON_API_BASE_URL 未配置：没有可用的正式 Amazon 数据源"
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_reviews_per_request = max_reviews_per_request
        self.timeout = timeout
        self._last_request_ts = 0.0

    async def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < MIN_REQUEST_INTERVAL:
            await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_ts = time.monotonic()

    async def _get_json(self, client: httpx.AsyncClient, url: str, params: dict) -> dict:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            await self._throttle()
            try:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "amazon provider request failed (attempt %d/%d): %s",
                    attempt, MAX_RETRIES, exc,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(0.5 * 2 ** (attempt - 1))
        raise UpstreamError(f"Amazon 数据源连续 {MAX_RETRIES} 次请求失败: {last_error}")

    async def fetch(
        self, asin: str, marketplace: str, window_months: int, max_reviews: int
    ) -> AmazonFetchResult:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            meta = await self._get_json(
                client, f"{self.base_url}/amazon/product", {"asin": asin, "marketplace": marketplace}
            )
            reviews: list[dict] = []
            page = 1
            while len(reviews) < max_reviews:
                payload = await self._get_json(
                    client,
                    f"{self.base_url}/amazon/reviews",
                    {"asin": asin, "marketplace": marketplace, "page": page},
                )
                batch = payload.get("reviews", [])
                if not batch:
                    break
                reviews.extend(batch)
                page += 1
            reviews = reviews[:max_reviews]

        metadata = ProductMetadata(
            asin=asin,
            title=str(meta.get("title") or asin),
            marketplace=marketplace,
            category=meta.get("category"),
            current_price=meta.get("current_price"),
            currency=meta.get("currency", "USD"),
            main_image_url=meta.get("main_image_url"),
            length_cm=meta.get("length_cm"),
            width_cm=meta.get("width_cm"),
            height_cm=meta.get("height_cm"),
            weight_kg=meta.get("weight_kg"),
            bsr=meta.get("bsr"),
            bsr_category=meta.get("bsr_category"),
        )
        return AmazonFetchResult(
            metadata=metadata,
            reviews=[normalize_review(r, asin) for r in reviews],
        )
