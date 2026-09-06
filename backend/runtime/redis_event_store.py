"""Redis-backed EventStore — production SSE event path.

Recent events live in a per-task Redis list (bounded), fan-out uses pub/sub,
so a reconnecting client can always recover the latest state.
"""

import json
from typing import AsyncIterator

from redis.asyncio import Redis

from runtime.event_store import TaskEvent


class RedisEventStore:
    MAX_HISTORY = 200

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def _events_key(task_id: str) -> str:
        return f"insightx:events:{task_id}"

    @staticmethod
    def _channel(task_id: str) -> str:
        return f"insightx:chan:{task_id}"

    async def publish(self, event: TaskEvent) -> None:
        payload = event.model_dump_json()
        key = self._events_key(event.task_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.rpush(key, payload)
            pipe.ltrim(key, -self.MAX_HISTORY, -1)
            pipe.publish(self._channel(event.task_id), payload)
            await pipe.execute()

    async def recent(self, task_id: str, limit: int = 50) -> list[TaskEvent]:
        raw = await self._redis.lrange(self._events_key(task_id), -limit, -1)
        return [TaskEvent.model_validate(json.loads(item)) for item in raw]

    async def latest(self, task_id: str) -> TaskEvent | None:
        raw = await self._redis.lindex(self._events_key(task_id), -1)
        return TaskEvent.model_validate(json.loads(raw)) if raw else None

    async def subscribe(self, task_id: str) -> AsyncIterator[TaskEvent]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel(task_id))
        try:
            async for msg in pubsub.listen():
                if msg.get("type") != "message":
                    continue
                yield TaskEvent.model_validate(json.loads(msg["data"]))
        finally:
            await pubsub.aclose()
