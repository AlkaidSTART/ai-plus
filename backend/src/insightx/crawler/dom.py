"""DOM serialization contracts, hashing, and atomic JSON persistence."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

DomNode = dict[str, Any]
SKIPPED_TAGS = frozenset({"script", "style", "noscript", "template"})
FORMAT_VERSION: Literal["1"] = "1"

DOM_SERIALIZER_SCRIPT = r"""
() => {
  const skippedTags = new Set(["script", "style", "noscript", "template"]);

  const serialize = (node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent || "";
      return text.trim() === "" ? null : {type: "text", text};
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return null;
    }

    const tag = node.tagName.toLowerCase();
    if (skippedTags.has(tag)) {
      return null;
    }

    const attributes = {};
    for (const attribute of Array.from(node.attributes)) {
      attributes[attribute.name] = attribute.value;
    }

    const children = [];
    for (const child of Array.from(node.childNodes)) {
      const serialized = serialize(child);
      if (serialized !== null) {
        children.push(serialized);
      }
    }

    return {type: "element", tag, attributes, children};
  };

  return serialize(document.documentElement);
};
"""


class CrawlSnapshot(TypedDict):
    """Deterministic on-disk representation of one captured page."""

    format_version: Literal["1"]
    snapshot_id: str
    source_url: str
    final_url: str
    title: str
    captured_at: str
    http_status: int
    dom_sha256: str
    dom: DomNode


def utc_isoformat(value: datetime) -> str:
    """Render a datetime as UTC ISO 8601 with microsecond precision."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return (
        value.astimezone(UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def canonical_dom_json(dom: DomNode) -> str:
    """Serialize a DOM node with stable key ordering and compact separators."""

    validate_dom_node(dom)
    return json.dumps(
        dom,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def dom_sha256(dom: DomNode) -> str:
    """Return the SHA-256 digest of the canonical DOM JSON."""

    return hashlib.sha256(canonical_dom_json(dom).encode("utf-8")).hexdigest()


def validate_dom_node(node: object, *, path: str = "$") -> None:
    """Validate the fixed element/text DOM contract."""

    if not isinstance(node, dict):
        raise ValueError(f"{path}: DOM node must be an object")

    node_type = node.get("type")
    if node_type == "text":
        if set(node) != {"type", "text"}:
            raise ValueError(f"{path}: text node has unexpected fields")
        text = node.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{path}: text node must contain non-whitespace text")
        return

    if node_type != "element":
        raise ValueError(f"{path}: unsupported DOM node type {node_type!r}")

    if set(node) != {"type", "tag", "attributes", "children"}:
        raise ValueError(f"{path}: element node has unexpected fields")

    tag = node.get("tag")
    if not isinstance(tag, str) or not tag or tag != tag.lower():
        raise ValueError(f"{path}: element tag must be a non-empty lowercase string")
    if tag in SKIPPED_TAGS:
        raise ValueError(f"{path}: skipped element {tag!r} must not be serialized")

    attributes = node.get("attributes")
    if not isinstance(attributes, dict):
        raise ValueError(f"{path}: element attributes must be an object")
    for name, value in attributes.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise ValueError(f"{path}: attributes must map strings to strings")

    children = node.get("children")
    if not isinstance(children, list):
        raise ValueError(f"{path}: element children must be a list")
    for index, child in enumerate(children):
        validate_dom_node(child, path=f"{path}.children[{index}]")


def build_snapshot(
    *,
    snapshot_id: str,
    source_url: str,
    final_url: str,
    title: str,
    captured_at: datetime,
    http_status: int,
    dom: Mapping[str, Any],
) -> CrawlSnapshot:
    """Build the fixed JSON envelope after validating the DOM."""

    dom_node = cast(DomNode, dict(dom))
    return {
        "format_version": FORMAT_VERSION,
        "snapshot_id": snapshot_id,
        "source_url": source_url,
        "final_url": final_url,
        "title": title,
        "captured_at": utc_isoformat(captured_at),
        "http_status": http_status,
        "dom_sha256": dom_sha256(dom_node),
        "dom": dom_node,
    }


def atomic_write_snapshot(output_dir: Path, snapshot: CrawlSnapshot) -> Path:
    """Write a snapshot with UTF-8 JSON and atomically replace the target."""

    snapshot_id = snapshot["snapshot_id"]
    if not snapshot_id:
        raise ValueError("snapshot_id must not be empty")

    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{snapshot_id}.json"

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target_dir,
            prefix=f".{snapshot_id}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(snapshot, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, target_path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise

    return target_path
