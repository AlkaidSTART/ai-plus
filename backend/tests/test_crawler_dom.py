from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from insightx.crawler.dom import (
    DOM_SERIALIZER_SCRIPT,
    DomNode,
    atomic_write_snapshot,
    build_snapshot,
    canonical_dom_json,
    dom_sha256,
    validate_dom_node,
)


def sample_dom() -> DomNode:
    return {
        "type": "element",
        "tag": "div",
        "attributes": {"class": "content"},
        "children": [{"type": "text", "text": "hello"}],
    }


def test_dom_sha256_uses_canonical_json() -> None:
    canonical = (
        '{"attributes":{"class":"content"},'
        '"children":[{"text":"hello","type":"text"}],'
        '"tag":"div","type":"element"}'
    )

    assert canonical_dom_json(sample_dom()) == canonical
    assert dom_sha256(sample_dom()) == hashlib.sha256(canonical.encode()).hexdigest()


def test_dom_sha256_is_independent_of_key_insertion_order() -> None:
    reordered: DomNode = {
        "children": [{"text": "hello", "type": "text"}],
        "attributes": {"class": "content"},
        "tag": "div",
        "type": "element",
    }

    assert dom_sha256(reordered) == dom_sha256(sample_dom())


def test_serializer_script_skips_non_visible_subtrees() -> None:
    for tag in ("script", "style", "noscript", "template"):
        assert f'"{tag}"' in DOM_SERIALIZER_SCRIPT


def test_build_snapshot_uses_utc_microseconds() -> None:
    captured_at = datetime(
        2026,
        9,
        14,
        12,
        30,
        tzinfo=timezone(timedelta(hours=8)),
    )

    snapshot = build_snapshot(
        snapshot_id="snapshot-1",
        source_url="https://example.com/start",
        final_url="https://example.com/final",
        title="Example",
        captured_at=captured_at,
        http_status=200,
        dom=sample_dom(),
    )

    assert snapshot["captured_at"] == "2026-09-14T04:30:00.000000Z"
    assert snapshot["dom_sha256"] == dom_sha256(sample_dom())
    assert snapshot["format_version"] == "1"


def test_atomic_write_snapshot_writes_utf8_json_without_temp_files(
    tmp_path: Path,
) -> None:
    snapshot = build_snapshot(
        snapshot_id="snapshot-utf8",
        source_url="https://example.com/start",
        final_url="https://example.com/final",
        title="中文标题",
        captured_at=datetime(2026, 9, 14, tzinfo=UTC),
        http_status=200,
        dom=sample_dom(),
    )

    written_path = atomic_write_snapshot(tmp_path, snapshot)

    assert written_path == tmp_path.resolve() / "snapshot-utf8.json"
    assert json.loads(written_path.read_text(encoding="utf-8")) == snapshot
    assert "中文标题" in written_path.read_text(encoding="utf-8")
    assert list(tmp_path.iterdir()) == [written_path]


@pytest.mark.parametrize(
    "node",
    [
        {"type": "text", "text": "   "},
        {"type": "text", "text": "hello", "extra": True},
        {"type": "element", "tag": "DIV", "attributes": {}, "children": []},
        {"type": "element", "tag": "div", "attributes": {"id": 1}, "children": []},
        {"type": "element", "tag": "script", "attributes": {}, "children": []},
        {"type": "unknown"},
    ],
)
def test_validate_dom_node_rejects_invalid_contract(node: object) -> None:
    with pytest.raises(ValueError):
        validate_dom_node(node)


def test_atomic_write_snapshot_cleans_temp_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = build_snapshot(
        snapshot_id="snapshot-replace-failure",
        source_url="https://example.com/start",
        final_url="https://example.com/final",
        title="Example",
        captured_at=datetime(2026, 9, 14, tzinfo=UTC),
        http_status=200,
        dom=sample_dom(),
    )

    def fail_replace(source: object, target: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("insightx.crawler.dom.os.replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        atomic_write_snapshot(tmp_path, snapshot)

    assert list(tmp_path.iterdir()) == []
