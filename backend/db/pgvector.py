"""Best-effort pgvector extension bootstrap.

Called during app startup; a failure (e.g. the DB user lacks superuser rights
or the extension is not installed on the server) is logged and left to the
deployment's own migration/bootstrap step.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def ensure_pgvector(engine: AsyncEngine) -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        return True
    except Exception as exc:  # noqa: BLE001 - any DB error must not block startup
        logger.warning("pgvector extension bootstrap skipped: %s", exc)
        return False
