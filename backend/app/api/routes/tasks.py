"""任务路由（api.md §3–§4、§7）。创建做真实参数校验，执行逻辑 501 占位。"""

import re

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from app.api.errors import ErrorCode, error_response, not_implemented
from app.api.schemas import CreateTaskRequest

router = APIRouter(tags=["insight-task"])

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


def _validate_asins(asins: list[str]) -> JSONResponse | None:
    seen = {a.upper() for a in asins}
    if len(seen) == 0 or len(seen) > 10:
        return error_response(422, ErrorCode.INVALID_INPUT, "去重后 ASIN 必须为 1–10 个")
    for a in asins:
        if not ASIN_RE.match(a.upper()):
            return error_response(
                422, ErrorCode.INVALID_ASIN, f"ASIN 必须为 10 位字母或数字：{a}"
            )
    return None


@router.post("/insight/task", status_code=202)
def create_task(
    body: CreateTaskRequest, idempotency_key: str = Header(alias="Idempotency-Key")
) -> JSONResponse:
    if body.platform != "amazon" or body.marketplace != "US":
        return error_response(422, ErrorCode.INVALID_INPUT, "P0 仅支持 amazon/US")
    if bad := _validate_asins(body.asins):
        return bad
    _ = idempotency_key
    return not_implemented()


@router.get("/insight/tasks")
def list_tasks() -> JSONResponse:
    return not_implemented()


@router.get("/insight/task/{task_id}")
def get_task(task_id: str) -> JSONResponse:
    _ = task_id
    return not_implemented()


@router.post("/insight/task/{task_id}/cancel", status_code=202)
def cancel_task(task_id: str) -> JSONResponse:
    _ = task_id
    return not_implemented()


@router.post("/insight/task/{task_id}/retry", status_code=202)
def retry_task(
    task_id: str, idempotency_key: str = Header(alias="Idempotency-Key")
) -> JSONResponse:
    _ = (task_id, idempotency_key)
    return not_implemented()
