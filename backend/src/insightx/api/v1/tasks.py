"""Task management endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from insightx.database import SessionFactory, get_session
from insightx.dependencies import IdempotencyKey, LimitQuery, get_tenant_id
from insightx.schemas import (
    EvidenceResponse,
    EvidenceSourceType,
    ExtractAsinsRequest,
    ExtractAsinsResponse,
    FinancialEvaluateRequest,
    FinancialEvaluateResponse,
    Page,
    ProductItem,
    ReportResponse,
    RetryTaskRequest,
    SearchProductsRequest,
    SearchProductsResponse,
    SuccessEnvelope,
    TaskCreatedResponse,
    TaskCreateRequest,
    TaskListItem,
    TaskSnapshot,
    TaskStatus,
)
from insightx.services import financial as financial_svc
from insightx.services import tasks as task_svc

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/extract-asins")
def extract_asins_endpoint(
    body: ExtractAsinsRequest,
) -> SuccessEnvelope[ExtractAsinsResponse]:
    from insightx.services.asin import extract_asins

    raw_text = body.text or ""
    if body.urls:
        raw_text += " " + " ".join(body.urls)
    asins = extract_asins(raw_text, limit=10)
    return SuccessEnvelope(data=ExtractAsinsResponse(asins=asins))


@router.post("/search-products")
async def search_products_endpoint(
    body: SearchProductsRequest,
) -> SuccessEnvelope[SearchProductsResponse]:
    from insightx.services.search import search_amazon_products

    products = await search_amazon_products(body.keyword, limit=body.limit)
    product_items = [
        ProductItem(
            asin=p["asin"],
            title=p["title"],
            rating=p.get("rating"),
            url=p["url"],
        )
        for p in products
    ]
    return SuccessEnvelope(
        data=SearchProductsResponse(keyword=body.keyword, products=product_items)
    )


@router.post("", status_code=202)
def create_task(
    body: TaskCreateRequest,
    idempotency_key: IdempotencyKey,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
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
    session: Session = Depends(get_session),  # noqa: B008
    status: TaskStatus | None = Query(None),  # noqa: B008
    cursor: str | None = Query(None),  # noqa: B008
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
    session: Session = Depends(get_session),  # noqa: B008
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
    response: Response,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
) -> SuccessEnvelope[TaskSnapshot]:
    snapshot, first_request = task_svc.cancel_task(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
    )
    response.status_code = 202 if first_request else 200
    return SuccessEnvelope(data=snapshot)


@router.post("/{task_id}/retry", status_code=202)
def retry_task(
    task_id: str,
    body: RetryTaskRequest,
    idempotency_key: IdempotencyKey,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
) -> SuccessEnvelope[TaskCreatedResponse]:
    result = task_svc.retry_task(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        request=body,
        idempotency_key=idempotency_key,
    )
    return SuccessEnvelope(data=result)


@router.get("/{task_id}/items/{item_id}/report")
def get_report(
    task_id: str,
    item_id: str,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
) -> SuccessEnvelope[ReportResponse]:
    report = task_svc.get_report(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        item_id=item_id,
    )
    return SuccessEnvelope(data=report)


@router.get("/{task_id}/items/{item_id}/evidence")
def list_evidence(
    task_id: str,
    item_id: str,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
    claim_id: str | None = Query(None),  # noqa: B008
    source_type: EvidenceSourceType | None = Query(None),  # noqa: B008
    cursor: str | None = Query(None),
    limit: LimitQuery = 20,
) -> SuccessEnvelope[Page[EvidenceResponse]]:
    page = task_svc.list_evidence(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        item_id=item_id,
        claim_id=claim_id,
        source_type=source_type,
        cursor=cursor,
        limit=limit,
    )
    return SuccessEnvelope(data=page)


@router.get("/{task_id}/export")
def export_task(
    task_id: str,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
) -> Response:
    content, filename = task_svc.export_task_charter(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
    )
    ascii_filename = f"task_{task_id}_charter.zip"
    quoted_filename = quote(filename)
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_filename}"; '
                f"filename*=UTF-8''{quoted_filename}"
            )
        },
    )


@router.get("/{task_id}/events")
async def task_events(
    task_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    after: Annotated[str | None, Query(alias="after")] = None,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    session_factory: SessionFactory = request.app.state.session_factory
    cursor = last_event_id if last_event_id is not None else after
    prepared_cursor = await run_in_threadpool(
        task_svc.prepare_event_stream,
        session_factory,
        tenant_id=tenant_id,
        task_id=task_id,
        cursor=cursor,
    )

    async def generate() -> AsyncIterator[str]:
        event_cursor = prepared_cursor
        last_frame_at = asyncio.get_running_loop().time()
        yield "retry: 3000\n\n"
        while True:
            if await request.is_disconnected():
                break
            events = await run_in_threadpool(
                task_svc.fetch_task_events,
                session_factory,
                task_id=task_id,
                tenant_id=tenant_id,
                after_event_id=event_cursor,
            )
            for event in events:
                yield (
                    f"id: {event['id']}\nevent: {event['type']}\n"
                    f"data: {json.dumps(event)}\n\n"
                )
                event_cursor = int(event["id"])
                last_frame_at = asyncio.get_running_loop().time()
            terminal = await run_in_threadpool(
                task_svc.task_is_terminal,
                session_factory,
                tenant_id=tenant_id,
                task_id=task_id,
            )
            if terminal and not events:
                break
            now = asyncio.get_running_loop().time()
            if now - last_frame_at >= 15:
                timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                yield f": keep-alive {timestamp}\n\n"
                last_frame_at = now
            await asyncio.sleep(0.5)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/{task_id}/items/{item_id}/financial")
def get_item_financial(
    task_id: str,
    item_id: str,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
) -> SuccessEnvelope[FinancialEvaluateResponse]:
    result = financial_svc.get_task_item_financial(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        item_id=item_id,
    )
    return SuccessEnvelope(data=result)


@router.post("/{task_id}/items/{item_id}/financial")
def evaluate_item_financial(
    task_id: str,
    item_id: str,
    body: FinancialEvaluateRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
) -> SuccessEnvelope[FinancialEvaluateResponse]:
    body.task_id = task_id
    body.item_id = item_id
    result = financial_svc.evaluate_financial_risk(
        body,
        session=session,
        tenant_id=tenant_id,
    )
    return SuccessEnvelope(data=result)
