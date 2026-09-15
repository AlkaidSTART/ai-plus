"""MongoDB persistence for immutable raw DOM snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, IndexModel
from pymongo.asynchronous.collection import AsyncCollection

from insightx.crawler.dom import CrawlSnapshot


class DomSnapshotStore:
    """Persist crawler snapshots in a MongoDB collection."""

    def __init__(
        self,
        uri: str,
        database: str,
        collection: str,
        *,
        client: AsyncMongoClient[dict[str, Any]] | None = None,
    ) -> None:
        self._client = client or AsyncMongoClient(uri)
        self._collection: AsyncCollection[dict[str, Any]] = self._client.get_database(
            database
        ).get_collection(collection)
        self._indexes_ready = False
        self._closed = False

    async def ensure_indexes(self) -> None:
        """Create the required non-unique snapshot indexes once per instance."""

        if self._indexes_ready:
            return

        await self._collection.create_indexes(
            [
                IndexModel(
                    [
                        ("source_url", ASCENDING),
                        ("captured_at", DESCENDING),
                    ],
                    name="source_url_captured_at",
                ),
                IndexModel(
                    [("dom_sha256", ASCENDING)],
                    name="dom_sha256",
                ),
                IndexModel(
                    [
                        ("tenant_id", ASCENDING),
                        ("task_id", ASCENDING),
                        ("task_item_id", ASCENDING),
                        ("captured_at", DESCENDING),
                    ],
                    name="tenant_task_captured_at",
                ),
            ]
        )
        self._indexes_ready = True

    async def save_snapshot(
        self,
        *,
        snapshot: CrawlSnapshot,
        captured_at: datetime,
        json_path: Path,
        tenant_id: str | None = None,
        task_id: str | None = None,
        task_item_id: str | None = None,
    ) -> None:
        """Insert one immutable snapshot document using its stable ID."""

        await self.ensure_indexes()

        captured_at_utc = captured_at
        if captured_at_utc.tzinfo is None:
            captured_at_utc = captured_at_utc.replace(tzinfo=UTC)
        captured_at_utc = captured_at_utc.astimezone(UTC)

        document: dict[str, Any] = {
            "_id": snapshot["snapshot_id"],
            "source_url": snapshot["source_url"],
            "final_url": snapshot["final_url"],
            "title": snapshot["title"],
            "captured_at": captured_at_utc,
            "http_status": snapshot["http_status"],
            "dom_format_version": snapshot["format_version"],
            "dom_sha256": snapshot["dom_sha256"],
            "dom": snapshot["dom"],
            "json_path": str(Path(json_path).expanduser().resolve()),
            "crawler": {"engine": "playwright", "browser": "chromium"},
        }
        if tenant_id is not None:
            document["tenant_id"] = tenant_id
        if task_id is not None:
            document["task_id"] = task_id
        if task_item_id is not None:
            document["task_item_id"] = task_item_id

        await self._collection.insert_one(document)

    async def close(self) -> None:
        """Close the underlying client once."""

        if self._closed:
            return
        await self._client.close()
        self._closed = True
