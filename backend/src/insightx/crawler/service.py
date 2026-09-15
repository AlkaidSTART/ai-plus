"""End-to-end orchestration for one URL crawl."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
from uuid import uuid4

from insightx.crawler.config import CrawlerSettings
from insightx.crawler.dom import CrawlSnapshot, atomic_write_snapshot, build_snapshot
from insightx.crawler.fetch import FetchedPage, fetch_dom
from insightx.crawler.storage import DomSnapshotStore


class Fetcher(Protocol):
    """Callable contract used to keep crawl orchestration testable."""

    async def __call__(
        self,
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage: ...


@dataclass(frozen=True, slots=True)
class CrawlResult:
    """Public result of one successful crawl."""

    snapshot_id: str
    json_path: Path
    dom_sha256: str
    final_url: str
    http_status: int


def validate_http_url(url: str) -> str:
    """Require an absolute HTTP(S) URL."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute http:// or https:// URL")
    if parsed.hostname is None:
        raise ValueError("URL must include a valid hostname")
    return url


async def crawl_url(
    url: str,
    *,
    settings: CrawlerSettings,
    store: DomSnapshotStore,
    tenant_id: str | None = None,
    task_id: str | None = None,
    task_item_id: str | None = None,
    fetcher: Fetcher = fetch_dom,
) -> CrawlResult:
    """Capture a URL, persist its JSON, then persist it to MongoDB."""

    source_url = validate_http_url(url)
    fetched = await fetcher(
        source_url,
        timeout_ms=settings.crawler_timeout_ms,
        headless=settings.crawler_headless,
    )

    snapshot_id = uuid4().hex
    snapshot: CrawlSnapshot = build_snapshot(
        snapshot_id=snapshot_id,
        source_url=fetched.source_url,
        final_url=fetched.final_url,
        title=fetched.title,
        captured_at=fetched.captured_at,
        http_status=fetched.http_status,
        dom=fetched.dom,
    )

    json_path = atomic_write_snapshot(settings.crawler_output_dir, snapshot)
    await store.save_snapshot(
        snapshot=snapshot,
        captured_at=fetched.captured_at,
        json_path=json_path,
        tenant_id=tenant_id,
        task_id=task_id,
        task_item_id=task_item_id,
    )

    return CrawlResult(
        snapshot_id=snapshot_id,
        json_path=json_path,
        dom_sha256=snapshot["dom_sha256"],
        final_url=fetched.final_url,
        http_status=fetched.http_status,
    )
