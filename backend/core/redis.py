"""Shared async Redis client lifecycle."""

import logging

import redis.asyncio as aioredis
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        from core.config import get_settings

        _client = aioredis.from_url(
            get_settings().REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2.0,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:  # noqa: BLE001
            logger.warning("redis close failed", exc_info=True)
    _client = None
