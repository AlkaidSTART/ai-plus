"""报告与证据路由（api.md §5）。P0 原文证据先行，全部 501 占位。"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import not_implemented

router = APIRouter(tags=["insight-report"])


@router.get("/insight/task/{task_id}/items/{item_id}/report")
def get_report(task_id: str, item_id: str) -> JSONResponse:
    _ = (task_id, item_id)
    return not_implemented()


@router.get("/insight/task/{task_id}/items/{item_id}/evidence")
def get_evidence(task_id: str, item_id: str, report_id: str) -> JSONResponse:
    _ = (task_id, item_id, report_id)
    return not_implemented()
