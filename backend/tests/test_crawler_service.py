from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from insightx.crawler.config import CrawlerSettings
from insightx.crawler.dom import DomNode
from insightx.crawler.fetch import FetchedPage
from insightx.crawler.service import crawl_url, validate_http_url


class RecordingStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def save_snapshot(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


class FailingStore(RecordingStore):
    async def save_snapshot(self, **kwargs: Any) -> None:
        raise RuntimeError("mongo unavailable")


def sample_dom() -> DomNode:
    return {
        "type": "element",
        "tag": "html",
        "attributes": {"lang": "en"},
        "children": [{"type": "text", "text": "captured"}],
    }


@pytest.mark.parametrize(
    "url",
    [
        "example.com",
        "ftp://example.com",
        "https://",
        "not a url",
    ],
)
def test_validate_http_url_rejects_non_http_absolute_urls(url: str) -> None:
    with pytest.raises(ValueError, match="absolute http"):
        validate_http_url(url)


async def test_crawl_url_fetches_then_writes_json_then_mongodb(tmp_path: Path) -> None:
    events: list[str] = []
    captured_at = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)

    async def fetcher(
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage:
        events.append("fetch")
        assert url == "https://example.com/start"
        assert timeout_ms == 12_345
        assert headless is False
        return FetchedPage(
            source_url=url,
            final_url="https://example.com/final",
            title="Example",
            http_status=200,
            captured_at=captured_at,
            dom=sample_dom(),
        )

    class OrderedStore(RecordingStore):
        async def save_snapshot(self, **kwargs: Any) -> None:
            events.append("mongo")
            json_path = kwargs["json_path"]
            assert json_path.is_file()
            snapshot = json.loads(json_path.read_text(encoding="utf-8"))
            assert snapshot["title"] == "Example"
            await super().save_snapshot(**kwargs)

    store = OrderedStore()
    settings = CrawlerSettings(
        crawler_output_dir=tmp_path,
        crawler_timeout_ms=12_345,
        crawler_headless=False,
    )

    result = await crawl_url(
        "https://example.com/start",
        settings=settings,
        store=store,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        task_id="task-1",
        task_item_id="item-1",
        fetcher=fetcher,
    )

    assert events == ["fetch", "mongo"]
    assert result.json_path.is_file()
    assert result.final_url == "https://example.com/final"
    assert result.http_status == 200
    assert len(result.dom_sha256) == 64
    snapshot = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert snapshot["snapshot_id"] == result.snapshot_id
    assert snapshot["dom"] == sample_dom()
    assert store.calls == [
        {
            "snapshot": snapshot,
            "captured_at": captured_at,
            "json_path": result.json_path,
            "tenant_id": "tenant-1",
            "task_id": "task-1",
            "task_item_id": "item-1",
        }
    ]


async def test_crawl_url_propagates_fetch_failure_without_writing(
    tmp_path: Path,
) -> None:
    async def failing_fetcher(
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage:
        raise RuntimeError("browser failed")

    store = RecordingStore()
    settings = CrawlerSettings(crawler_output_dir=tmp_path)

    with pytest.raises(RuntimeError, match="browser failed"):
        await crawl_url(
            "https://example.com/start",
            settings=settings,
            store=store,  # type: ignore[arg-type]
            fetcher=failing_fetcher,
        )

    assert store.calls == []
    assert list(tmp_path.iterdir()) == []


async def test_crawl_url_propagates_mongodb_failure_after_json_write(
    tmp_path: Path,
) -> None:
    async def fetcher(
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage:
        return FetchedPage(
            source_url=url,
            final_url=url,
            title="Example",
            http_status=200,
            captured_at=datetime(2026, 9, 14, tzinfo=UTC),
            dom=sample_dom(),
        )

    settings = CrawlerSettings(crawler_output_dir=tmp_path)

    with pytest.raises(RuntimeError, match="mongo unavailable"):
        await crawl_url(
            "https://example.com/start",
            settings=settings,
            store=FailingStore(),  # type: ignore[arg-type]
            fetcher=fetcher,
        )

    assert len(list(tmp_path.glob("*.json"))) == 1


async def test_crawl_url_propagates_json_write_failure_without_mongodb_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fetcher(
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage:
        return FetchedPage(
            source_url=url,
            final_url=url,
            title="Example",
            http_status=200,
            captured_at=datetime(2026, 9, 14, tzinfo=UTC),
            dom=sample_dom(),
        )

    def fail_write(output_dir: Path, snapshot: object) -> Path:
        raise OSError("disk unavailable")

    monkeypatch.setattr(
        "insightx.crawler.service.atomic_write_snapshot",
        fail_write,
    )
    store = RecordingStore()
    settings = CrawlerSettings(crawler_output_dir=tmp_path)

    with pytest.raises(OSError, match="disk unavailable"):
        await crawl_url(
            "https://example.com/start",
            settings=settings,
            store=store,  # type: ignore[arg-type]
            fetcher=fetcher,
        )

    assert store.calls == []
