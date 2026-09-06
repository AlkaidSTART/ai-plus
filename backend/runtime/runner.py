"""Workflow runner: schedules the LangGraph for a task and drives task state.

创建任务 → 保存 Task → 调度 LangGraph → 更新状态 → 发布事件
→ 保存 final_report → COMPLETED / FAILED
"""

import asyncio
import logging
from datetime import UTC, datetime

from agents.nodes import NODE_MESSAGES, STEP_BY_NODE
from agents.state import InsightState
from runtime.event_store import TaskEvent
from runtime.task_store import TaskRecord, TaskStatus, TaskStore
from runtime.event_store import EventStore

logger = logging.getLogger(__name__)

TERMINAL_STEPS = {"COMPLETED", "FAILED", "CANCELED"}


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class TaskCanceled(Exception):
    pass


def build_initial_state(task: TaskRecord) -> InsightState:
    return InsightState(
        task_id=task.task_id,
        asin=task.asin,
        platform=task.platform,
        marketplace=task.marketplace,
        review_window_months=task.review_window_months,
        max_reviews=task.max_reviews,
        financial_constraint=task.financial_constraint,
        options=task.options.model_dump(),
        retry_count=0,
        veto_status="PENDING",
        progress=0,
    )


class WorkflowRunner:
    def __init__(self, graph, task_store: TaskStore, event_store: EventStore) -> None:
        self.graph = graph
        self.task_store = task_store
        self.event_store = event_store
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._running: set[str] = set()

    def register(self, task_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._cancel_events[task_id] = event
        return event

    def unregister(self, task_id: str) -> None:
        self._cancel_events.pop(task_id, None)
        self._running.discard(task_id)

    def request_cancel(self, task_id: str) -> None:
        event = self._cancel_events.get(task_id)
        if event is not None:
            event.set()

    def is_running(self, task_id: str) -> bool:
        return task_id in self._running

    def _publish(self, task_id: str, step: str, progress: int, message: str, extra: dict) -> TaskEvent:
        return TaskEvent(
            task_id=task_id, step=step, progress=progress, message=message, extra=extra
        )

    async def run_task(self, task_id: str) -> None:
        task = await self.task_store.get(task_id)
        if task is None:
            logger.error("runner: task %s not found", task_id)
            return
        self._running.add(task_id)
        cancel_event = self.register(task_id)
        try:
            await self.task_store.update(
                task_id, status=TaskStatus.RUNNING, started_at=_now_iso()
            )
            state = build_initial_state(task)
            summary: dict = {}
            async for chunk in self.graph.astream(state, stream_mode="updates"):
                if cancel_event.is_set():
                    raise TaskCanceled()
                for node_name, partial in chunk.items():
                    if not isinstance(partial, dict):
                        continue
                    await self._on_node_update(task_id, node_name, partial)
                    if node_name == "finalize":
                        summary = partial.get("final_report", {}).get("summary", {})
                        final_report = partial.get("final_report")
                        await self.task_store.update(
                            task_id,
                            summary=summary,
                            final_report=final_report,
                        )
            await self.task_store.update(
                task_id, status=TaskStatus.COMPLETED, progress=100, finished_at=_now_iso()
            )
            task = await self.task_store.get(task_id)
            veto_status = (summary or {}).get("veto_status", "PENDING")
            await self.event_store.publish(
                self._publish(
                    task_id,
                    "COMPLETED",
                    100,
                    "任务完成",
                    {
                        "review_count": (summary or {}).get("review_count"),
                        "cluster_count": (summary or {}).get("cluster_count"),
                        "proposal_count": (summary or {}).get("proposal_count"),
                        "veto_status": veto_status,
                    },
                )
            )
        except TaskCanceled:
            await self.task_store.update(
                task_id, status=TaskStatus.CANCELED, finished_at=_now_iso()
            )
            await self.event_store.publish(
                self._publish(task_id, "CANCELED", 0, "任务已取消", {})
            )
        except Exception as exc:  # noqa: BLE001 - any node failure → FAILED task
            logger.exception("runner: task %s failed", task_id)
            message = str(exc) or exc.__class__.__name__
            await self.task_store.update(
                task_id, status=TaskStatus.FAILED, error_message=message, finished_at=_now_iso()
            )
            await self.event_store.publish(
                self._publish(task_id, "FAILED", 0, message, {})
            )
        finally:
            self.unregister(task_id)

    async def _on_node_update(self, task_id: str, node_name: str, partial: dict) -> None:
        step, low, high = STEP_BY_NODE.get(node_name, (node_name.upper(), 0, 0))
        progress = int(partial.get("progress", low))
        extra: dict = {}
        if node_name == "fetch_reviews":
            extra["reviews_fetched"] = len(partial.get("raw_reviews", []))
        elif node_name == "vision_audit":
            extra["images_audited"] = len(partial.get("visual_evidences", []))
        elif node_name == "semantic_cluster":
            extra["cluster_count"] = len(partial.get("clustered_issues", []))
        elif node_name == "financial_veto":
            extra["retry_count"] = partial.get("retry_count", 0)
            extra["veto_status"] = partial.get("veto_status")
        elif node_name == "finalize":
            progress = 100

        fields: dict = {"current_node": node_name, "progress": progress}
        if "retry_count" in partial:
            fields["retry_count"] = int(partial["retry_count"])
        await self.task_store.update(task_id, **fields)
        await self.event_store.publish(
            self._publish(task_id, step, progress, NODE_MESSAGES.get(node_name, node_name), extra)
        )
