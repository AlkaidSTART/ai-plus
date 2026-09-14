from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from pymongo import IndexModel

from insightx.crawler.dom import CrawlSnapshot
from insightx.crawler.storage import DomSnapshotStore


class FakeCollection:
    def __init__(self) -> None:
        self.create_indexes = AsyncMock()
        self.insert_one = AsyncMock()


class FakeDatabase:
    def __init__(self, collection: FakeCollection) -> None:
        self.collection = collection
        self.requested_names: list[str] = []

    def get_collection(self, name: str) -> FakeCollection:
        self.requested_names.append(name)
        return self.collection


class FakeClient:
    def __init__(self, database: FakeDatabase) -> None:
        self.database = database
        self.requested_names: list[str] = []
        self.close = AsyncMock()

    def get_database(self, name: str) -> FakeDatabase:
        self.requested_names.append(name)
        return self.database


def sample_snapshot() -> CrawlSnapshot:
    return {
        "format_version": "1",
        "snapshot_id": "snapshot-123",
        "source_url": "https://example.com/start",
        "final_url": "https://example.com/final",
        "title": "Example",
        "captured_at": "2026-09-14T04:30:00.000000Z",
        "http_status": 200,
        "dom_sha256": "a" * 64,
        "dom": {
            "type": "element",
            "tag": "html",
            "attributes": {},
            "children": [],
        },
    }


async def test_save_snapshot_creates_indexes_and_inserts_contract(
    tmp_path: Path,
) -> None:
    collection = FakeCollection()
    database = FakeDatabase(collection)
    client = FakeClient(database)
    store = DomSnapshotStore(
        "mongodb://example",
        "insightx",
        "dom_snapshots",
        client=client,  # type: ignore[arg-type]
    )

    await store.save_snapshot(
        snapshot=sample_snapshot(),
        captured_at=datetime(2026, 9, 14, 12, 30),
        json_path=tmp_path / "snapshot-123.json",
        tenant_id="tenant-1",
        task_id="task-1",
        task_item_id="item-1",
    )

    assert client.requested_names == ["insightx"]
    assert database.requested_names == ["dom_snapshots"]
    collection.create_indexes.assert_awaited_once()
    indexes: list[IndexModel] = collection.create_indexes.await_args.args[0]
    assert [index.document["name"] for index in indexes] == [
        "source_url_captured_at",
        "dom_sha256",
        "tenant_task_captured_at",
    ]
    assert [index.document.get("unique", False) for index in indexes] == [
        False,
        False,
        False,
    ]

    document: dict[str, Any] = collection.insert_one.await_args.args[0]
    assert document["_id"] == "snapshot-123"
    assert document["captured_at"] == datetime(2026, 9, 14, 12, 30, tzinfo=UTC)
    assert document["json_path"] == str((tmp_path / "snapshot-123.json").resolve())
    assert document["crawler"] == {"engine": "playwright", "browser": "chromium"}
    assert document["tenant_id"] == "tenant-1"
    assert document["task_id"] == "task-1"
    assert document["task_item_id"] == "item-1"


async def test_save_snapshot_omits_optional_scope_fields(tmp_path: Path) -> None:
    collection = FakeCollection()
    client = FakeClient(FakeDatabase(collection))
    store = DomSnapshotStore(
        "mongodb://example",
        "insightx",
        "dom_snapshots",
        client=client,  # type: ignore[arg-type]
    )

    await store.save_snapshot(
        snapshot=sample_snapshot(),
        captured_at=datetime(2026, 9, 14, tzinfo=UTC),
        json_path=tmp_path / "snapshot-123.json",
    )

    document = collection.insert_one.await_args.args[0]
    assert "tenant_id" not in document
    assert "task_id" not in document
    assert "task_item_id" not in document


async def test_indexes_and_close_are_idempotent(tmp_path: Path) -> None:
    collection = FakeCollection()
    client = FakeClient(FakeDatabase(collection))
    store = DomSnapshotStore(
        "mongodb://example",
        "insightx",
        "dom_snapshots",
        client=client,  # type: ignore[arg-type]
    )

    await store.ensure_indexes()
    await store.ensure_indexes()
    await store.close()
    await store.close()

    collection.create_indexes.assert_awaited_once()
    client.close.assert_awaited_once_with()
