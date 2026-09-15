"""Utilities for extracting Amazon Standard Identification Numbers (ASINs) from text and URLs."""

from __future__ import annotations

import re
from collections.abc import Sequence

# Regex matching 10-char alphanumeric ASIN in Amazon URL paths or parameters
_AMAZON_ASIN_URL_RE = re.compile(
    r"(?:/(?:dp|gp/product|product|gp/aw/d|d)/|[?&]asin=)([A-Z0-9]{10})(?:[/?&#\s]|$)",
    re.IGNORECASE,
)

_STANDALONE_ASIN_RE = re.compile(r"^[A-Z0-9]{10}$", re.IGNORECASE)


def extract_asin(text: str) -> str | None:
    """Extract a single 10-character uppercase ASIN from a URL or raw ASIN string."""

    cleaned = text.strip()
    if not cleaned:
        return None

    if _STANDALONE_ASIN_RE.match(cleaned):
        return cleaned.upper()

    match = _AMAZON_ASIN_URL_RE.search(cleaned)
    if match:
        return match.group(1).upper()

    # Fallback: check if text contains an isolated 10-char alphanumeric token
    tokens = re.split(r"[\s/]+", cleaned)
    for token in tokens:
        clean_token = token.split("?")[0].split("#")[0].strip()
        if _STANDALONE_ASIN_RE.match(clean_token):
            return clean_token.upper()

    return None


def extract_asins(text: str, *, limit: int = 10) -> list[str]:
    """Extract, deduplicate, and limit ASINs from arbitrary text containing URLs or ASINs."""

    if not text or not text.strip():
        return []

    tokens = re.split(r"[\s,，;；\n\r\t]+", text.strip())
    results: list[str] = []
    seen: set[str] = set()

    for token in tokens:
        asin = extract_asin(token)
        if asin and asin not in seen:
            seen.add(asin)
            results.append(asin)
            if len(results) >= limit:
                break

    return results


def normalize_asin_list(inputs: Sequence[str], *, max_count: int = 10) -> list[str]:
    """Normalize a list of strings that may contain ASINs or product URLs."""

    results: list[str] = []
    seen: set[str] = set()

    for item in inputs:
        asin = extract_asin(str(item))
        if asin and asin not in seen:
            seen.add(asin)
            results.append(asin)
            if len(results) >= max_count:
                break

    return results
