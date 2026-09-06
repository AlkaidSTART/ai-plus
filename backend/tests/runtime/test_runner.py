"""Runtime runner tests (offline, in-memory stores)."""

from agents.workflow import build_graph, create_insight_graph
from runtime.event_store import InMemoryEventStore
from runtime.runner import WorkflowRunner
from runtime.task_store import InMemoryTaskStore, TaskRecord, TaskStatus
from services.providers import DeterministicProviders

CONSTRAINT_VETO = {
    "mold_cost_usd": 0,
    "moq": 1000,
    "current_gross_margin": 0.32,
    "expected_price_usd": 29.99,
    "unit_cost_increase_usd": 1800,
}


def make_task(task_id: str = "tsk_runner", **overrides) -> TaskRecord:
    record = TaskRecord(task_id=task_id, asin="B0C1234ABC")
    for key, value in overrides.items():
        setattr(record, key, value)
    return record


def make_runner() -> tuple[WorkflowRunner, InMemoryTaskStore, InMemoryEventStore]:
    task_store = InMemoryTaskStore()
    event_store = InMemoryEventStore()
    runner = WorkflowRunner(create_insight_graph(), task_store, event_store)
    return runner, task_store, event_store


async def test_pending_to_completed():
    runner, task_store, event_store = make_runner()
    task = make_task()
    await task_store.create(task)
    await runner.run_task(task.task_id)

    final = await task_store.get(task.task_id)
    assert final.status == TaskStatus.COMPLETED
    assert final.started_at is not None
    assert final.finished_at is not None
    assert final.progress == 100
    assert final.current_node == "finalize"
    assert (final.summary.review_count or 0) > 0
    assert final.final_report is not None


async def test_exception_marks_failed():
    task_store = InMemoryTaskStore()
    event_store = InMemoryEventStore()
    providers = DeterministicProviders()

    async def boom(*args, **kwargs):
        raise ValueError("provider down")

    providers.reviews.fetch = boom
    runner = WorkflowRunner(build_graph(providers), task_store, event_store)
    task = make_task()
    await task_store.create(task)

    await runner.run_task(task.task_id)
    final = await task_store.get(task.task_id)
    assert final.status == TaskStatus.FAILED
    assert "provider down" in final.error_message
    assert final.finished_at is not None


async def test_progress_and_current_node_progression():
    runner, task_store, event_store = make_runner()
    task = make_task()
    await task_store.create(task)
    await runner.run_task(task.task_id)
    final = await task_store.get(task.task_id)
    assert final.progress == 100

    events = await event_store.recent(task.task_id)
    steps = [e.step for e in events]
    assert steps[0] == "FETCHING_DATA"
    assert steps[-1] == "COMPLETED"
    for expected in (
        "FETCHING_DATA",
        "VISION_AUDIT",
        "SEMANTIC_CLUSTER",
        "DUAL_DECISION",
        "FINANCIAL_VETO",
        "EVIDENCE_TRACE",
        "COMPLETED",
    ):
        assert expected in steps


async def test_retry_exhausted_marks_vetoed_and_converges():
    providers = DeterministicProviders()
    original = providers.decision.decide

    async def always_veto(task_id, clusters, constraint, retry_count):
        proposals = await original(task_id, clusters, constraint, retry_count)
        for p in proposals:
            p["cost_estimation_usd"] = 5_000_000
        return proposals

    providers.decision.decide = always_veto
    task_store = InMemoryTaskStore()
    event_store = InMemoryEventStore()
    runner = WorkflowRunner(build_graph(providers), task_store, event_store)
    task = make_task(financial_constraint=CONSTRAINT_VETO)
    await task_store.create(task)

    await runner.run_task(task.task_id)  # must not loop forever
    final = await task_store.get(task.task_id)
    assert final.status == TaskStatus.COMPLETED
    assert final.retry_count == 2
    assert final.summary.veto_status == "VETOED"

    events = await event_store.recent(task.task_id)
    veto_events = [e for e in events if e.step == "FINANCIAL_VETO"]
    assert len(veto_events) == 3
    assert [e.extra["retry_count"] for e in veto_events] == [0, 1, 2]
