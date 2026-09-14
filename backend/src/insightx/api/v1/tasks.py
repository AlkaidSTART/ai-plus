"""Task management endpoints."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from insightx.database import SessionFactory, get_session
from insightx.dependencies import IdempotencyKey, LimitQuery, get_tenant_id
from insightx.schemas import (
    Page,
    SuccessEnvelope,
    TaskCreateRequest,
    TaskCreatedResponse,
    TaskListItem,
    TaskSnapshot,
    TaskStatus,
)
from insightx.services import tasks as task_svc

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", status_code=202)
def create_task(
    body: TaskCreateRequest,
    idempotency_key: IdempotencyKey,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> SuccessEnvelope[TaskCreatedResponse]:
    result = task_svc.create_task(
        session,
        tenant_id=tenant_id,
        request=body,
        idempotency_key=idempotency_key,
    )
    return SuccessEnvelope(data=result)


@router.get("")
def list_tasks(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
    status: TaskStatus | None = Query(None),
    cursor: str | None = Query(None),
    limit: LimitQuery = 20,
) -> SuccessEnvelope[Page[TaskListItem]]:
    page = task_svc.list_tasks(
        session,
        tenant_id=tenant_id,
        status=status,
        cursor=cursor,
        limit=limit,
    )
    return SuccessEnvelope(data=page)


@router.get("/{task_id}")
def get_task(
    task_id: str,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> SuccessEnvelope[TaskSnapshot]:
    snapshot = task_svc.get_task_snapshot(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
    )
    return SuccessEnvelope(data=snapshot)


@router.post("/{task_id}/cancel")
def cancel_task(
    task_id: str,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> SuccessEnvelope[TaskSnapshot]:
    snapshot, _ = task_svc.cancel_task(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
    )
    return SuccessEnvelope(data=snapshot)


@router.get("/{task_id}/events")
async def task_events(
    task_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    last_event_id: Annotated[str | None, Query(alias="cursor")] = None,
) -> StreamingResponse:
    session_factory: SessionFactory = request.app.state.session_factory
    cursor = task_svc.prepare_event_stream(
        session_factory,
        tenant_id=tenant_id,
        task_id=task_id,
        cursor=last_event_id,
    )

    async def generate():  # noqa: ANN202
        after = cursor
        while True:
            if await request.is_disconnected():
                break
            events = task_svc.fetch_task_events(
                session_factory,
                task_id=task_id,
                after_event_id=after,
            )
            for event in events:
                yield f"id: {event['id']}\nevent: {event['type']}\ndata: {json.dumps(event)}\n\n"
                after = int(event["id"])
            if task_svc.task_is_terminal(
                session_factory,
                tenant_id=tenant_id,
                task_id=task_id,
            ):
                if not events:
                    break
            else:
                await asyncio.sleep(1)

    return StreamingResponse(generate(), media_type="text/event-stream")
