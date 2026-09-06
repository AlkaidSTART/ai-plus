"""Task event storage and fan-out for SSE.

`EventStore` is the production-facing interface:

- :class:`InMemoryEventStore` — tests / offline demo (asyncio queues).
- A Redis-backed store (list for recent events + pub/sub for fan-out) is the
  production main path, wired in the workflow step.
"""

import asyncio
import json
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class TaskEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str
    step: str
    progress: int = 0
    message: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=utc_now_iso)

    def to_sse(self) -> str:
        return f"event: message\ndata: {json.dumps(self.model_dump(), ensure_ascii=False)}\n\n"


def new_task_id() -> str:
    return f"tsk_{uuid.uuid4().hex[:8]}"


class EventStore:
    async def publish(self, event: TaskEvent) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def recent(self, task_id: str, limit: int = 50) -> list[TaskEvent]:  # pragma: no cover
        raise NotImplementedError

    async def latest(self, task_id: str) -> TaskEvent | None:  # pragma: no cover - interface
        raise NotImplementedError

    def subscribe(self, task_id: str) -> AsyncIterator[TaskEvent]:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryEventStore(EventStore):
    """Single-process event store; each subscriber gets its own queue."""

    def __init__(self, max_history: int = 200) -> None:
        self._history: dict[str, deque[TaskEvent]] = defaultdict(lambda: deque(maxlen=max_history))
        self._queues: dict[str, list[asyncio.Queue[TaskEvent]]] = defaultdict(list)

    async def publish(self, event: TaskEvent) -> None:
        self._history[event.task_id].append(event)
        for queue in list(self._queues.get(event.task_id, [])):
            await queue.put(event)

    async def recent(self, task_id: str, limit: int = 50) -> list[TaskEvent]:
        history = list(self._history.get(task_id, []))
        return history[-limit:]

    async def latest(self, task_id: str) -> TaskEvent | None:
        history = self._history.get(task_id)
        return history[-1] if history else None

    async def subscribe(self, task_id: str) -> AsyncIterator[TaskEvent]:
        queue: asyncio.Queue[TaskEvent] = asyncio.Queue()
        self._queues[task_id].append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._queues[task_id].remove(queue)
