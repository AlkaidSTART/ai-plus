"""任务路由（api.md §3–§4、§7）。创建做真实参数校验并持久化；报告/SSE 仍 501。"""

import re
import uuid

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.api.errors import ErrorCode, error_response
from app.api.schemas import (
    CancelResponse,
    CreateTaskRequest,
    RetryRequest,
    RetryTaskResponse,
    TaskCreatedResponse,
    TaskListResponse,
    TaskSnapshotResponse,
    TaskStatus,
)
from app.db.session import get_session
from app.services import tasks as task_svc

router = APIRouter(tags=["insight-task"])

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


def _validate_asins(asins: list[str]) -> JSONResponse | None:
    normalized = task_svc.normalize_asins(asins)
    if len(normalized) == 0 or len(normalized) > 10:
        return error_response(422, ErrorCode.INVALID_INPUT, "去重后 ASIN 必须为 1–10 个")
    for a in normalized:
        if not ASIN_RE.match(a):
            return error_response(
                422, ErrorCode.INVALID_ASIN, f"ASIN 必须为 10 位字母或数字：{a}"
            )
    return None


def _parse_uuid(value: str, field: str) -> uuid.UUID | JSONResponse:
    try:
        return uuid.UUID(value)
    except ValueError:
        return error_response(422, ErrorCode.INVALID_INPUT, f"{field} 必须为 UUID")


@router.post("/insight/task", status_code=202, response_model=TaskCreatedResponse)
async def create_task(
    body: CreateTaskRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    if body.platform != "amazon" or body.marketplace != "US":
        return error_response(422, ErrorCode.INVALID_INPUT, "P0 仅支持 amazon/US")
    if bad := _validate_asins(body.asins):
        return bad
    project_id = _parse_uuid(body.project_id, "project_id")
    if isinstance(project_id, JSONResponse):
        return project_id
    try:
        return await task_svc.create_task(
            session,
            tenant_id=tenant_id,
            project_id=project_id,
            platform=body.platform,
            marketplace=body.marketplace,
            asins=body.asins,
            window_given=body.window,
            idempotency_key=idempotency_key,
        )
    except task_svc.ProjectNotFound:
        return error_response(404, ErrorCode.NOT_FOUND, "项目不存在或不属于当前企业")
    except task_svc.IdempotencyConflict:
        return error_response(
            409,
            ErrorCode.IDEMPOTENCY_CONFLICT,
            "相同幂等键提交了不同内容",
            details=[{"field": "Idempotency-Key", "reason": "conflict"}],
        )
    except ValueError as exc:
        return error_response(422, ErrorCode.INVALID_INPUT, str(exc))


@router.get("/insight/tasks", response_model=TaskListResponse)
async def list_tasks(
    project_id: str | None = None,
    status: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    project_uuid = None
    if project_id is not None:
        project_uuid = _parse_uuid(project_id, "project_id")
        if isinstance(project_uuid, JSONResponse):
            return project_uuid
    task_status = None
    if status is not None:
        try:
            task_status = TaskStatus(status).value
        except ValueError:
            return error_response(422, ErrorCode.INVALID_INPUT, "status 非法")
    try:
        items, next_cursor = await task_svc.list_tasks(
            session,
            tenant_id=tenant_id,
            project_id=project_uuid,
            status=task_status,
            cursor=cursor,
            limit=max(1, min(limit, task_svc.TASK_LIST_MAX_LIMIT)),
        )
    except ValueError as exc:
        return error_response(422, ErrorCode.INVALID_INPUT, str(exc))
    return {"items": items, "next_cursor": next_cursor}


@router.get("/insight/task/{task_id}", response_model=TaskSnapshotResponse)
async def get_task(
    task_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    parsed = _parse_uuid(task_id, "task_id")
    if isinstance(parsed, JSONResponse):
        return parsed
    snapshot = await task_svc.get_snapshot(session, tenant_id, parsed)
    if snapshot is None:
        return error_response(404, ErrorCode.NOT_FOUND, "任务不存在或不属于当前企业")
    return snapshot


@router.post(
    "/insight/task/{task_id}/cancel", status_code=202, response_model=CancelResponse
)
async def cancel_task(
    task_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    parsed = _parse_uuid(task_id, "task_id")
    if isinstance(parsed, JSONResponse):
        return parsed
    result = await task_svc.cancel_task(session, tenant_id, parsed)
    if result is None:
        return error_response(404, ErrorCode.NOT_FOUND, "任务不存在或不属于当前企业")
    if result["status"] in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED):
        return JSONResponse(
            status_code=200, content=CancelResponse(**result).model_dump(mode="json")
        )
    return result


@router.post(
    "/insight/task/{task_id}/retry", status_code=202, response_model=RetryTaskResponse
)
async def retry_task(
    task_id: str,
    body: RetryRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    parsed = _parse_uuid(task_id, "task_id")
    if isinstance(parsed, JSONResponse):
        return parsed
    try:
        return await task_svc.retry_task(
            session,
            tenant_id=tenant_id,
            source_task_id=parsed,
            item_ids=body.item_ids,
            idempotency_key=idempotency_key,
        )
    except task_svc.TaskNotFound:
        return error_response(404, ErrorCode.NOT_FOUND, "源任务不存在或不属于当前企业")
    except task_svc.NotRetryable:
        return error_response(
            409, ErrorCode.ITEM_NOT_RETRYABLE, "仅已终结任务的 FAILED 分项可重试"
        )
    except task_svc.IdempotencyConflict:
        return error_response(
            409,
            ErrorCode.IDEMPOTENCY_CONFLICT,
            "相同幂等键提交了不同内容",
            details=[{"field": "Idempotency-Key", "reason": "conflict"}],
        )
    except ValueError as exc:
        return error_response(422, ErrorCode.INVALID_INPUT, str(exc))
