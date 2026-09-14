"""Command-line entry point for one raw DOM crawl."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from insightx.crawler.config import CrawlerSettings
from insightx.crawler.service import crawl_url, validate_http_url
from insightx.crawler.storage import DomSnapshotStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m insightx.crawler",
        description="Capture one rendered DOM and persist JSON + MongoDB.",
    )
    parser.add_argument("--url", required=True, help="Absolute http:// or https:// URL")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--task-item-id", default=None)
    return parser


async def _run(args: argparse.Namespace, settings: CrawlerSettings) -> int:
    store: DomSnapshotStore | None = None
    try:
        store = DomSnapshotStore(
            settings.mongodb_uri,
            settings.mongodb_database,
            settings.mongodb_dom_collection,
        )
        result = await crawl_url(
            args.url,
            settings=settings,
            store=store,
            tenant_id=args.tenant_id,
            task_id=args.task_id,
            task_item_id=args.task_item_id,
        )
    except Exception as exc:
        if store is not None:
            try:
                await store.close()
            except Exception as cleanup_exc:
                print(
                    f"crawler cleanup failed after crawl failure: {cleanup_exc}",
                    file=sys.stderr,
                )
        print(f"crawler failed: {exc}", file=sys.stderr)
        return 1

    try:
        await store.close()
    except Exception as exc:
        print(f"crawler cleanup failed: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "snapshot_id": result.snapshot_id,
                "json_path": str(result.json_path),
                "dom_sha256": result.dom_sha256,
                "final_url": result.final_url,
                "http_status": result.http_status,
            },
            ensure_ascii=False,
        )
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, run one crawl, and return a process status code."""

    args = _build_parser().parse_args(argv)
    try:
        validate_http_url(args.url)
        settings = CrawlerSettings().with_cli_overrides(
            output_dir=args.output_dir,
            headed=args.headed,
        )
    except (ValidationError, ValueError) as exc:
        print(f"invalid crawler configuration: {exc}", file=sys.stderr)
        return 2

    return asyncio.run(_run(args, settings))


if __name__ == "__main__":
    raise SystemExit(main())
