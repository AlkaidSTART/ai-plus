"""Playwright + MongoDB raw DOM snapshot crawler."""

from insightx.crawler.config import CrawlerSettings
from insightx.crawler.dom import (
    DOM_SERIALIZER_SCRIPT,
    CrawlSnapshot,
    DomNode,
    atomic_write_snapshot,
    build_snapshot,
    canonical_dom_json,
    dom_sha256,
    validate_dom_node,
)
from insightx.crawler.fetch import FetchedPage, fetch_dom, fetch_with_playwright
from insightx.crawler.service import CrawlResult, crawl_url, validate_http_url
from insightx.crawler.storage import DomSnapshotStore

__all__ = [
    "DOM_SERIALIZER_SCRIPT",
    "CrawlResult",
    "CrawlSnapshot",
    "CrawlerSettings",
    "DomNode",
    "DomSnapshotStore",
    "FetchedPage",
    "atomic_write_snapshot",
    "build_snapshot",
    "canonical_dom_json",
    "crawl_url",
    "dom_sha256",
    "fetch_dom",
    "fetch_with_playwright",
    "validate_dom_node",
    "validate_http_url",
]
