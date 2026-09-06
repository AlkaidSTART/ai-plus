"""Unified response envelope and pagination schemas (docs/api.md §1.2)."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """All REST responses use `{code, message, data}`."""

    code: int = 0
    message: str = "ok"
    data: T | None = None


class PageData(BaseModel, Generic[T]):
    items: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class Page(Envelope[PageData[T]], Generic[T]):
    pass
