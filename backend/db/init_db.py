"""Database bootstrap: pgvector extension + schema creation.

Alembic migrations can be introduced later; until then the official schema
(SQLAlchemy models) is created idempotently at startup.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from db import models  # noqa: F401 - register all models on Base.metadata
from db.base import Base
from db.pgvector import ensure_pgvector

logger = logging.getLogger(__name__)


async def init_db(engine: AsyncEngine) -> None:
    try:
        await ensure_pgvector(engine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001 - startup must not crash without DB
        logger.warning("database bootstrap skipped: %s", exc)
