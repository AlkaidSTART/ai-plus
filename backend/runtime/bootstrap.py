"""Runtime assembly: stores + runner, selected by configuration.

- TASK_STORE_BACKEND=memory (default, dev/test) → InMemoryTaskStore
- TASK_STORE_BACKEND=db     (production)       → DbTaskStore (PostgreSQL)
- EVENT_STORE_BACKEND=memory (default)        → InMemoryEventStore
- EVENT_STORE_BACKEND=redis  (production)     → RedisEventStore
"""

from dataclasses import dataclass

from agents.workflow import create_insight_graph, build_graph
from core.config import Settings
from runtime.event_store import EventStore, InMemoryEventStore
from runtime.redis_event_store import RedisEventStore
from runtime.runner import WorkflowRunner
from runtime.task_store import InMemoryTaskStore, TaskStore


@dataclass
class Runtime:
    task_store: TaskStore
    event_store: EventStore
    runner: WorkflowRunner


def build_graph_for_settings(settings: Settings):
    if settings.PROVIDER_MODE == "real":
        from services.real_providers import RealProviders

        return build_graph(RealProviders(settings))
    return create_insight_graph()


def build_runtime(settings: Settings) -> Runtime:
    task_store: TaskStore
    if settings.TASK_STORE_BACKEND == "db":
        from runtime.db_task_store import DbTaskStore

        task_store = DbTaskStore()
    else:
        task_store = InMemoryTaskStore()

    event_store: EventStore
    if settings.EVENT_STORE_BACKEND == "redis":
        from core.redis import get_redis
        from runtime.redis_event_store import RedisEventStore

        event_store = RedisEventStore(get_redis())
    else:
        event_store = InMemoryEventStore()

    runner = WorkflowRunner(build_graph_for_settings(settings), task_store, event_store)
    return Runtime(task_store=task_store, event_store=event_store, runner=runner)
