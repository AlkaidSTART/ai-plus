"""SSE 事件流（api.md §6）。实现前返回 501，不伪造 text/event-stream。"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import not_implemented

router = APIRouter(tags=["insight-events"])


@router.get("/insight/task/{task_id}/events")
def task_events(task_id: str, after: str = "0") -> JSONResponse:
    _ = (task_id, after)
    return not_implemented()
