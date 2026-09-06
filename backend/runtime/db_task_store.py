"""PostgreSQL-backed TaskStore — the production task state main path."""

from typing import Any

from db.repositories.task_repository import TaskRepository
from db.session import get_sessionmaker
from runtime.task_store import TaskRecord, TaskStatus, TaskStore


class DbTaskStore(TaskStore):
    def __init__(self, sessionmaker=None) -> None:
        self._sessionmaker = sessionmaker

    def _maker(self):
        return self._sessionmaker or get_sessionmaker()

    async def create(self, task: TaskRecord) -> TaskRecord:
        async with self._maker()() as session:
            return await TaskRepository(session).create(task)

    async def get(self, task_id: str) -> TaskRecord | None:
        async with self._maker()() as session:
            return await TaskRepository(session).get(task_id)

    async def update(self, task_id: str, **fields: Any) -> TaskRecord | None:
        async with self._maker()() as session:
            return await TaskRepository(session).update(task_id, fields)

    async def list(
        self,
        status: TaskStatus | None = None,
        asin: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TaskRecord], int]:
        async with self._maker()() as session:
            return await TaskRepository(session).list(status, asin, page, page_size)
