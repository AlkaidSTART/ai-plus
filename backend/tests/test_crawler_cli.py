from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from insightx.crawler import __main__ as cli
from insightx.crawler.config import CrawlerSettings
from insightx.crawler.service import CrawlResult


class FakeStore:
    instances: list[FakeStore] = []

    def __init__(self, uri: str, database: str, collection: str) -> None:
        self.uri = uri
        self.database = database
        self.collection = collection
        self.closed = False
        self.instances.append(self)

    async def close(self) -> None:
        self.closed = True


def test_parser_requires_url() -> None:
    with pytest.raises(SystemExit):
        cli._build_parser().parse_args([])


def test_main_rejects_non_http_url(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["--url", "file:///tmp/example.html"])

    assert status == 2
    assert "absolute http:// or https:// URL" in capsys.readouterr().err


def test_main_applies_headed_override_and_prints_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    async def fake_crawl_url(url: str, **kwargs: Any) -> CrawlResult:
        captured["url"] = url
        captured.update(kwargs)
        return CrawlResult(
            snapshot_id="snapshot-123",
            json_path=tmp_path / "snapshot-123.json",
            dom_sha256="a" * 64,
            final_url="https://example.com/final",
            http_status=200,
        )

    FakeStore.instances.clear()
    monkeypatch.setattr(cli, "DomSnapshotStore", FakeStore)
    monkeypatch.setattr(cli, "crawl_url", fake_crawl_url)

    status = cli.main(
        [
            "--url",
            "https://example.com/start",
            "--output-dir",
            str(tmp_path),
            "--headed",
            "--tenant-id",
            "tenant-1",
        ]
    )

    assert status == 0
    settings = captured["settings"]
    assert isinstance(settings, CrawlerSettings)
    assert settings.crawler_headless is False
    assert settings.crawler_output_dir == tmp_path
    assert captured["tenant_id"] == "tenant-1"
    assert len(FakeStore.instances) == 1
    assert FakeStore.instances[0].closed is True
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "snapshot_id": "snapshot-123",
        "json_path": str(tmp_path / "snapshot-123.json"),
        "dom_sha256": "a" * 64,
        "final_url": "https://example.com/final",
        "http_status": 200,
    }


def test_main_returns_nonzero_when_crawl_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def failing_crawl_url(url: str, **kwargs: Any) -> CrawlResult:
        raise RuntimeError("storage unavailable")

    FakeStore.instances.clear()
    monkeypatch.setattr(cli, "DomSnapshotStore", FakeStore)
    monkeypatch.setattr(cli, "crawl_url", failing_crawl_url)

    status = cli.main(["--url", "https://example.com/start"])

    assert status == 1
    assert "crawler failed: storage unavailable" in capsys.readouterr().err
    assert FakeStore.instances[0].closed is True
