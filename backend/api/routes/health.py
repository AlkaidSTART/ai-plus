"""Health check (docs/api.md §3.1).

Reports real DB / Redis connectivity; never returns `true` for a dependency
that is not reachable.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_app_settings, get_db, get_redis_dep
from api.schemas.common import Envelope
from core.config import Settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["system"])


class HealthData(BaseModel):
    status: str
    version: str
    db: bool
    redis: bool


@router.get("", response_model=Envelope[HealthData])
async def health(
    session: AsyncSession = Depends(get_db),
    redis: object = Depends(get_redis_dep),
    settings: Settings = Depends(get_app_settings),
) -> Envelope[HealthData]:
    db_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001 - health must report, not raise
        logger.warning("health: database unreachable", exc_info=True)

    redis_ok = False
    try:
        redis_ok = bool(await redis.ping())
    except Exception:  # noqa: BLE001
        logger.warning("health: redis unreachable", exc_info=True)

    status = "ok" if db_ok and redis_ok else "degraded"
    return Envelope(
        data=HealthData(status=status, version=settings.APP_VERSION, db=db_ok, redis=redis_ok)
    )
