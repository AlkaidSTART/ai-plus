"""DB 测试支撑：隔离 PostgreSQL 门控、无插件 asyncio 入口、schema 与清理。

约定：DB 测试只跑在隔离 PostgreSQL 上（`TEST_DATABASE_URL` 优先，
否则沿用 `DATABASE_URL` 默认本地库）；不可达则跳过，不用 SQLite 代替
UUID/约束/事务语义。调用方须用 fresh session，本模块不维护全局连接。
"""

import asyncio
import os
import socket
import urllib.parse

import pytest
from sqlalchemy import text

from app.config import settings, sync_db_url
from app.db.base import Base


def _pg_reachable() -> bool:
    url = os.getenv("TEST_DATABASE_URL", settings.database_url)
    parts = urllib.parse.urlparse(url)
    try:
        with socket.create_connection(
            (parts.hostname or "localhost", parts.port or 5432), timeout=0.5
        ):
            return True
    except OSError:
        return False


requires_pg = pytest.mark.skipif(
    not _pg_reachable(),
    reason="无隔离 PostgreSQL（TEST_DATABASE_URL 或默认库不可达）：DB 写入测试跳过",
)


def run(coro):
    """无 pytest-asyncio 时的同步入口：asyncio.run 包裹单个协程。"""
    return asyncio.run(coro)


async def reset_pg(session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        await session.execute(text(f'TRUNCATE "{table.name}" CASCADE'))
    await session.commit()


def ensure_schema(pg_url: str) -> None:
    from sqlalchemy import create_engine

    engine = create_engine(sync_db_url(pg_url))
    Base.metadata.create_all(engine)
    engine.dispose()


def pg_url() -> str:
    return os.getenv("TEST_DATABASE_URL", settings.database_url)
