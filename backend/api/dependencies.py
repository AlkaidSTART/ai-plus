"""Shared FastAPI dependencies."""

from collections.abc import AsyncIterator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings, get_settings
from core.redis import get_redis
from db.session import get_sessionmaker


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


def get_redis_dep() -> Redis:
    return get_redis()


def get_app_settings() -> Settings:
    return get_settings()
