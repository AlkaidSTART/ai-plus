"""Background task execution and pipeline runner for InsightX."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import socket
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from statistics import fmean
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from insightx.crawler.dom import DomNode
from insightx.crawler.fetch import FetchedPage, fetch_dom
from insightx.database import SessionFactory
from insightx.models import (
    Evidence,
    EvidenceClaimRef,
    OutboxMessage,
    Report,
    Task,
    TaskEvent,
    TaskItem,
    utc_now,
)
from insightx.schemas import (
    DataQuality,
    EvidenceSourceType,
    FinancialState,
    NodeStatus,
    ReportPainPoint,
    ReportProposal,
    TaskStatus,
)

logger = logging.getLogger(__name__)

_PIPELINE_NODES = (
    ("fetch_metadata", "商品元数据与评论抓取"),
    ("clean_and_embed", "评论文本清洗与向量化"),
    ("cluster_pain_points", "高频痛点聚类"),
    ("generate_proposals", "生成双栏改款建议"),
    ("build_report", "报告生成与证据归档"),
)
_OUTBOX_TOPIC = "task.created"
_LEASE_SECONDS = 90
_RETRY_DELAY_SECONDS = 5
_AMAZON_ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})", re.IGNORECASE)
_RATING_RE = re.compile(r"([0-5](?:\.\d+)?)\s+out\s+of\s+5\s+stars?", re.IGNORECASE)
_BOT_MARKERS = (
    "captcha",
    "robot check",
    "not a robot",
    "automated access",
    "enter the characters you see below",
)
_SIGNIN_MARKERS = ("/ap/signin", "/signin", "amazon sign-in")


class Fetcher(Protocol):
    """Async callable used by the worker to capture a rendered product page."""

    async def __call__(
        self,
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage: ...


class _CancellationRequested(Exception):
    """Internal control-flow signal raised at a safe cancellation boundary."""


class _PipelineFailure(Exception):
    """A pipeline error that should produce one structured failed node."""

    def __init__(self, error: dict[str, Any]) -> None:
        super().__init__(str(error.get("message", "pipeline failed")))
        self.error = error


CurrentNode = tuple[str, str, str, datetime]


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}-{uuid4().hex[:12]}"


def _task_error(
    code: str,
    message: str,
    *,
    retryable: bool,
) -> dict[str, Any]:
    return {"code": code, "message": message, "retryable": retryable}


def _emit_event(
    session: Session,
    task_id: str,
    event_type: str,
    payload: dict[str, Any],
    task_item_id: str | None = None,
) -> TaskEvent:
    event = TaskEvent(
        task_id=task_id,
        task_item_id=task_item_id,
        event_type=event_type,
        payload=payload,
        created_at=utc_now(),
    )
    session.add(event)
    session.flush()
    return event


def _emit_node(
    session: Session,
    task_id: str,
    item_id: str,
    node_id: str,
    node_name: str,
    status: NodeStatus,
    *,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    duration_ms: int | None = None,
    skip_reason: str | None = None,
    error: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "node_id": node_id,
        "node_name": node_name,
        "status": status.value,
        "started_at": (
            started_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if started_at
            else None
        ),
        "finished_at": (
            finished_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if finished_at
            else None
        ),
        "duration_ms": duration_ms,
        "skip_reason": skip_reason,
        "error": error,
    }
    if details:
        payload.update(details)
    _emit_event(
        session,
        task_id=task_id,
        event_type="task_item.node_progress",
        payload=payload,
        task_item_id=item_id,
    )


def _publish_outbox(
    session: Session,
    *,
    task_id: str,
    outbox_message_id: str | None,
    now: datetime,
) -> None:
    statement = update(OutboxMessage).where(
        OutboxMessage.aggregate_id == task_id,
        OutboxMessage.topic == _OUTBOX_TOPIC,
        OutboxMessage.status == "PENDING",
    )
    if outbox_message_id is not None:
        statement = statement.where(OutboxMessage.message_id == outbox_message_id)
    session.execute(
        statement.values(
            status="PUBLISHED",
            published_at=now,
            locked_by=None,
            locked_at=None,
        )
    )


def _claim_next_outbox(
    session_factory: SessionFactory,
    *,
    worker_id: str,
) -> tuple[str, str] | None:
    """Claim one ready or lease-expired outbox message with SKIP LOCKED."""

    now = utc_now()
    lease_cutoff = now - timedelta(seconds=_LEASE_SECONDS)
    with session_factory() as session:
        with session.begin():
            message = session.scalar(
                select(OutboxMessage)
                .where(
                    OutboxMessage.topic == _OUTBOX_TOPIC,
                    OutboxMessage.status == "PENDING",
                    OutboxMessage.available_at <= now,
                    or_(
                        OutboxMessage.locked_at.is_(None),
                        OutboxMessage.locked_at < lease_cutoff,
                    ),
                )
                .order_by(
                    OutboxMessage.created_at.asc(),
                    OutboxMessage.message_id.asc(),
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if message is None:
                return None
            message.locked_by = worker_id
            message.locked_at = now
            message.attempts += 1
            session.flush()
            return message.aggregate_id, message.message_id


def _start_or_resume_task(session: Session, task_id: str) -> Task | None:
    """Atomically enter RUNNING or finalize an already-requested cancellation."""

    now = utc_now()
    with session.begin():
        task = session.scalar(
            select(Task).where(Task.task_id == task_id).with_for_update()
        )
        if task is None:
            return None
        if task.cancel_requested_at is not None:
            _cancel_task(
                session,
                task=task,
                current_node=None,
                outbox_message_id=None,
                now=now,
            )
            return None
        if TaskStatus(task.status) not in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
            _publish_outbox(
                session,
                task_id=task.task_id,
                outbox_message_id=None,
                now=now,
            )
            return None

        was_queued = task.status == TaskStatus.QUEUED.value
        task.status = TaskStatus.RUNNING.value
        task.updated_at = now
        queued_items = list(
            session.scalars(
                select(TaskItem)
                .where(
                    TaskItem.task_id == task_id,
                    TaskItem.status == TaskStatus.QUEUED.value,
                )
                .order_by(TaskItem.item_id.asc())
                .with_for_update()
            ).all()
        )
        if was_queued:
            _emit_event(
                session,
                task_id=task_id,
                event_type="task.status_changed",
                payload={"status": TaskStatus.RUNNING.value},
            )
        for item in queued_items:
            item.status = TaskStatus.RUNNING.value
            item.updated_at = now
            _emit_event(
                session,
                task_id=task_id,
                event_type="task_item.status_changed",
                payload={"status": TaskStatus.RUNNING.value},
                task_item_id=item.item_id,
            )
        return task


def _cancellation_requested(session: Session, task_id: str) -> bool:
    session.expire_all()
    value = session.scalar(
        select(Task.cancel_requested_at).where(Task.task_id == task_id)
    )
    return value is not None


def _raise_if_cancel_requested(session: Session, task_id: str) -> None:
    if _cancellation_requested(session, task_id):
        raise _CancellationRequested


def _cancel_task(
    session: Session,
    *,
    task: Task,
    current_node: CurrentNode | None,
    outbox_message_id: str | None,
    now: datetime,
) -> None:
    if current_node is not None:
        item_id, node_id, node_name, started_at = current_node
        duration_ms = int((now - started_at).total_seconds() * 1000)
        _emit_node(
            session,
            task_id=task.task_id,
            item_id=item_id,
            node_id=node_id,
            node_name=node_name,
            status=NodeStatus.CANCELED,
            started_at=started_at,
            finished_at=now,
            duration_ms=duration_ms,
            skip_reason="CANCEL_REQUESTED",
        )
    items = list(
        session.scalars(
            select(TaskItem)
            .where(
                TaskItem.task_id == task.task_id,
                TaskItem.status.not_in(
                    [
                        TaskStatus.COMPLETED.value,
                        TaskStatus.FAILED.value,
                        TaskStatus.CANCELED.value,
                    ]
                ),
            )
            .order_by(TaskItem.item_id.asc())
        ).all()
    )
    for item in items:
        item.status = TaskStatus.CANCELED.value
        item.current_node = None
        item.updated_at = now
        _emit_event(
            session,
            task_id=task.task_id,
            event_type="task_item.status_changed",
            payload={"status": TaskStatus.CANCELED.value},
            task_item_id=item.item_id,
        )
    task.status = TaskStatus.CANCELED.value
    task.updated_at = now
    task.finished_at = now
    _emit_event(
        session,
        task_id=task.task_id,
        event_type="task.status_changed",
        payload={"status": TaskStatus.CANCELED.value},
    )
    _publish_outbox(
        session,
        task_id=task.task_id,
        outbox_message_id=outbox_message_id,
        now=now,
    )


def _cancel_current_item(
    session: Session,
    *,
    task_id: str,
    current_node: CurrentNode,
    outbox_message_id: str | None,
) -> None:
    now = utc_now()
    task = session.get(Task, task_id)
    if task is None:
        return
    item_id, node_id, node_name, started_at = current_node
    duration_ms = int((now - started_at).total_seconds() * 1000)
    _emit_node(
        session,
        task_id=task_id,
        item_id=item_id,
        node_id=node_id,
        node_name=node_name,
        status=NodeStatus.CANCELED,
        started_at=started_at,
        finished_at=now,
        duration_ms=duration_ms,
        skip_reason="CANCEL_REQUESTED",
    )
    item = session.get(TaskItem, item_id)
    if item is not None:
        item.status = TaskStatus.CANCELED.value
        item.current_node = None
        item.updated_at = now
        _emit_event(
            session,
            task_id=task_id,
            event_type="task_item.status_changed",
            payload={"status": TaskStatus.CANCELED.value},
            task_item_id=item_id,
        )
    _cancel_task(
        session,
        task=task,
        current_node=None,
        outbox_message_id=outbox_message_id,
        now=now,
    )


def _start_node(
    session: Session,
    *,
    task_id: str,
    item_id: str,
    node_id: str,
    node_name: str,
) -> datetime:
    now = utc_now()
    item = session.get(TaskItem, item_id)
    if item is not None:
        item.current_node = node_id
        item.updated_at = now
    _emit_node(
        session,
        task_id=task_id,
        item_id=item_id,
        node_id=node_id,
        node_name=node_name,
        status=NodeStatus.RUNNING,
        started_at=now,
    )
    return now


def _finish_node(
    session: Session,
    *,
    task_id: str,
    item_id: str,
    node_id: str,
    node_name: str,
    status: NodeStatus,
    started_at: datetime,
    skip_reason: str | None = None,
    error: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    now = utc_now()
    duration_ms = int((now - started_at).total_seconds() * 1000)
    _emit_node(
        session,
        task_id=task_id,
        item_id=item_id,
        node_id=node_id,
        node_name=node_name,
        status=status,
        started_at=started_at,
        finished_at=now,
        duration_ms=duration_ms,
        skip_reason=skip_reason,
        error=error,
        details=details,
    )
    item = session.get(TaskItem, item_id)
    if item is not None and item.current_node == node_id:
        item.current_node = None
        item.updated_at = now


def _node_text(node: DomNode) -> str:
    parts: list[str] = []

    def visit(current: DomNode) -> None:
        if current.get("type") == "text":
            text = current.get("text")
            if isinstance(text, str):
                parts.append(text)
            return
        children = current.get("children")
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    visit(child)

    visit(node)
    return " ".join(" ".join(parts).split())


def _iter_elements(node: DomNode) -> Iterator[DomNode]:
    if node.get("type") != "element":
        return
    yield node
    children = node.get("children")
    if not isinstance(children, list):
        return
    for child in children:
        if isinstance(child, dict):
            yield from _iter_elements(child)


def _attributes(node: DomNode) -> dict[str, str]:
    raw = node.get("attributes")
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in raw.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def _find_descendant(
    node: DomNode,
    predicate: Callable[[DomNode, dict[str, str]], bool],
) -> DomNode | None:
    for candidate in _iter_elements(node):
        attributes = _attributes(candidate)
        if predicate(candidate, attributes):
            return candidate
    return None


def _parse_review_node(
    node: DomNode,
    *,
    index: int,
) -> dict[str, Any] | None:
    attributes = _attributes(node)
    source_ref = attributes.get("id")
    if not source_ref:
        identified = _find_descendant(
            node,
            lambda _candidate, attrs: (
                attrs.get("id", "").startswith("R") and len(attrs.get("id", "")) >= 8
            ),
        )
        if identified is not None:
            source_ref = _attributes(identified).get("id")
    if not source_ref:
        source_ref = f"review:{index}"

    body_node = _find_descendant(
        node,
        lambda _candidate, attrs: (
            attrs.get("data-hook") == "review-body"
            or "review-text" in attrs.get("class", "")
        ),
    )
    body = _node_text(body_node) if body_node is not None else ""
    title_node = _find_descendant(
        node,
        lambda _candidate, attrs: attrs.get("data-hook") == "review-title",
    )
    title = _node_text(title_node) if title_node is not None else ""
    date_node = _find_descendant(
        node,
        lambda _candidate, attrs: attrs.get("data-hook") == "review-date",
    )
    review_date = _node_text(date_node) if date_node is not None else None
    full_text = _node_text(node)
    rating_match = _RATING_RE.search(full_text)
    rating = float(rating_match.group(1)) if rating_match else None
    if not body.strip() and not title.strip():
        return None
    return {
        "source_ref": source_ref,
        "excerpt": body.strip() or title.strip(),
        "title": title.strip() or None,
        "rating": rating,
        "review_date": review_date,
    }


def _extract_reviews(
    dom: DomNode, *, limit: int = 10
) -> tuple[list[dict[str, Any]], int]:
    raw_nodes = [
        node
        for node in _iter_elements(dom)
        if _attributes(node).get("data-hook") == "review"
    ]
    reviews: list[dict[str, Any]] = []
    seen_refs: set[str] = set()
    seen_hashes: set[str] = set()
    excluded_count = 0
    for index, node in enumerate(raw_nodes, start=1):
        parsed = _parse_review_node(node, index=index)
        if parsed is None:
            excluded_count += 1
            continue
        source_ref = str(parsed["source_ref"])
        body = str(parsed.get("excerpt", "")).strip()
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if source_ref in seen_refs or body_hash in seen_hashes:
            excluded_count += 1
            continue
        if len(reviews) >= limit:
            excluded_count += 1
            continue
        seen_refs.add(source_ref)
        seen_hashes.add(body_hash)
        parsed["raw_index"] = index
        reviews.append(parsed)
    return reviews, excluded_count


def _final_asin(final_url: str) -> str | None:
    match = _AMAZON_ASIN_RE.search(urlparse(final_url).path)
    return match.group(1).upper() if match else None


def _classify_page(page: FetchedPage, *, requested_asin: str) -> str:
    haystack = f"{page.final_url} {page.title} {_node_text(page.dom)}".lower()
    if any(marker in haystack for marker in _BOT_MARKERS):
        return "BOT_CHECK"
    if any(
        marker in page.final_url.lower() or marker in page.title.lower()
        for marker in _SIGNIN_MARKERS
    ):
        return "SIGNIN"
    final_asin = _final_asin(page.final_url)
    if final_asin is None:
        return "NON_PRODUCT_PAGE"
    if final_asin == requested_asin.upper():
        return "PRODUCT_PAGE"
    return "PRODUCT_PAGE_VARIANT_REDIRECT"


def _request_url(asin: str) -> str:
    return f"https://www.amazon.com/dp/{asin}?th=1&psc=1"


def _fetch_page(fetcher: Fetcher, url: str) -> FetchedPage:
    timeout_ms = int(os.environ.get("CRAWLER_TIMEOUT_MS", "45000"))
    headless = os.environ.get("CRAWLER_HEADLESS", "true").lower() not in {
        "0",
        "false",
        "no",
    }
    return asyncio.run(
        fetcher(
            url,
            timeout_ms=timeout_ms,
            headless=headless,
        )
    )


def _sample_metrics(
    *,
    window_preset: str,
    reviews: list[dict[str, Any]],
    excluded_review_count: int,
    missing_reasons: list[str],
) -> dict[str, Any]:
    ratings = [
        float(review["rating"])
        for review in reviews
        if isinstance(review.get("rating"), (int, float))
    ]
    average_rating = round(fmean(ratings), 2) if ratings else None
    negative_review_ratio = (
        round(sum(rating <= 2 for rating in ratings) / len(ratings), 4)
        if ratings
        else None
    )
    methodology = (
        "Amazon US 商品页 DOM 抽取、文本去噪与确定性统计；"
        "未调用嵌入或聚类模型，不生成无证据痛点。"
    )
    return {
        "raw_review_count": len(reviews) + excluded_review_count,
        "valid_review_count": len(reviews),
        "excluded_review_count": excluded_review_count,
        "average_rating": average_rating,
        "negative_review_ratio": negative_review_ratio,
        "pain_point_count_with_evidence": 0,
        "window": {"preset": window_preset},
        "methodology": methodology,
        "missing_reasons": missing_reasons,
    }


def _replace_evidence(
    session: Session,
    *,
    task: Task,
    item: TaskItem,
    reviews: list[dict[str, Any]],
    request_url: str,
    final_url: str,
    page_classification: str,
) -> list[str]:
    evidence_ids = list(
        session.scalars(
            select(Evidence.evidence_id).where(
                Evidence.task_id == task.task_id,
                Evidence.item_id == item.item_id,
            )
        ).all()
    )
    if evidence_ids:
        session.execute(
            delete(EvidenceClaimRef).where(
                EvidenceClaimRef.evidence_id.in_(evidence_ids)
            )
        )
        session.execute(delete(Evidence).where(Evidence.evidence_id.in_(evidence_ids)))

    created_ids: list[str] = []
    for review in reviews:
        ev_id = review.get("evidence_id") or _new_id("evd")
        created_ids.append(ev_id)
        session.add(
            Evidence(
                evidence_id=ev_id,
                tenant_id=task.tenant_id,
                task_id=task.task_id,
                item_id=item.item_id,
                source_type=EvidenceSourceType.REVIEW_TEXT.value,
                source_ref=str(review["source_ref"]),
                excerpt=str(review["excerpt"]),
                source_url=final_url,
                published_at=None,
                source_metadata={
                    "asin": item.asin,
                    "rating": review.get("rating"),
                    "title": review.get("title"),
                    "review_date": review.get("review_date"),
                },
                provenance={
                    "source": "amazon-us-product-page-dom",
                    "request_url": request_url,
                    "final_url": final_url,
                    "page_classification": page_classification,
                },
                created_at=utc_now(),
            )
        )
    return created_ids


def _persist_report(
    session: Session,
    *,
    task: Task,
    item: TaskItem,
    sample_metrics: dict[str, Any],
    warnings: list[dict[str, Any]],
    model_metadata: dict[str, Any],
    data_quality: DataQuality,
    pain_points: list[ReportPainPoint] | None = None,
    proposals: list[ReportProposal] | None = None,
) -> None:
    now = utc_now()
    report = session.scalar(
        select(Report).where(
            Report.task_id == task.task_id,
            Report.item_id == item.item_id,
        )
    )
    dumped_pain_points = [p.model_dump(mode="json") for p in (pain_points or [])]
    dumped_proposals = [p.model_dump(mode="json") for p in (proposals or [])]
    values: dict[str, Any] = {
        "data_quality": data_quality.value,
        "sample_metrics": sample_metrics,
        "generated_at": now,
        "financial_state": FinancialState.NOT_EVALUATED.value,
        "pain_points": dumped_pain_points,
        "proposals": dumped_proposals,
        "warnings": warnings,
        "model_metadata": model_metadata,
    }
    if report is None:
        session.add(
            Report(
                report_id=_new_id("rpt"),
                tenant_id=task.tenant_id,
                task_id=task.task_id,
                item_id=item.item_id,
                **values,
            )
        )
    else:
        for key, value in values.items():
            setattr(report, key, value)

    # Persist claim references
    seen_refs: set[tuple[str, str]] = set()
    if pain_points:
        for p in pain_points:
            for ev_id in p.evidence_refs:
                pair = (ev_id, p.pain_point_id)
                if pair not in seen_refs:
                    seen_refs.add(pair)
                    session.add(
                        EvidenceClaimRef(
                            evidence_id=ev_id,
                            claim_id=p.pain_point_id,
                            claim_type="PAIN_POINT",
                        )
                    )
    if proposals:
        for prop in proposals:
            for ev_id in prop.evidence_refs:
                pair = (ev_id, prop.proposal_id)
                if pair not in seen_refs:
                    seen_refs.add(pair)
                    session.add(
                        EvidenceClaimRef(
                            evidence_id=ev_id,
                            claim_id=prop.proposal_id,
                            claim_type="PROPOSAL",
                        )
                    )

    item.data_quality = data_quality.value
    item.sample_metrics = sample_metrics
    item.error = None
    item.status = TaskStatus.COMPLETED.value
    item.current_node = None
    item.updated_at = now


def _complete_task(
    session: Session,
    *,
    task: Task,
    outbox_message_id: str | None,
) -> None:
    now = utc_now()
    if task.status != TaskStatus.COMPLETED.value:
        task.status = TaskStatus.COMPLETED.value
        task.updated_at = now
        task.finished_at = now
        _emit_event(
            session,
            task_id=task.task_id,
            event_type="task.status_changed",
            payload={"status": TaskStatus.COMPLETED.value},
        )
    _publish_outbox(
        session,
        task_id=task.task_id,
        outbox_message_id=outbox_message_id,
        now=now,
    )


def _fail_task(
    session_factory: SessionFactory,
    *,
    task_id: str,
    error: dict[str, Any],
    node_id: str,
    node_name: str,
    item_id: str | None,
    started_at: datetime | None,
    outbox_message_id: str | None,
    emit_node: bool = True,
) -> None:
    with session_factory() as session:
        with session.begin():
            task = session.get(Task, task_id)
            if task is None:
                return
            now = utc_now()
            if emit_node and started_at is not None and item_id is not None:
                duration_ms = int((now - started_at).total_seconds() * 1000)
                item = session.get(TaskItem, item_id)
                if item is not None:
                    _emit_node(
                        session,
                        task_id=task_id,
                        item_id=item.item_id,
                        node_id=node_id,
                        node_name=node_name,
                        status=NodeStatus.FAILED,
                        started_at=started_at,
                        finished_at=now,
                        duration_ms=duration_ms,
                        error=error,
                    )
            items = list(
                session.scalars(
                    select(TaskItem).where(TaskItem.task_id == task_id)
                ).all()
            )
            for item in items:
                if TaskStatus(item.status) not in {
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELED,
                }:
                    item.status = TaskStatus.FAILED.value
                    item.error = error
                    item.current_node = None
                    item.updated_at = now
                    _emit_event(
                        session,
                        task_id=task_id,
                        event_type="task_item.status_changed",
                        payload={"status": TaskStatus.FAILED.value},
                        task_item_id=item.item_id,
                    )
            task.status = TaskStatus.FAILED.value
            task.updated_at = now
            task.finished_at = now
            _emit_event(
                session,
                task_id=task_id,
                event_type="task.status_changed",
                payload={"status": TaskStatus.FAILED.value},
            )
            _publish_outbox(
                session,
                task_id=task_id,
                outbox_message_id=outbox_message_id,
                now=now,
            )


def execute_task_pipeline(
    session_factory: SessionFactory,
    task_id: str,
    *,
    fetcher: Fetcher = fetch_dom,
    outbox_message_id: str | None = None,
) -> None:
    """Execute one real task item pipeline using short database transactions."""

    with session_factory() as session:
        task = _start_or_resume_task(session, task_id)
        if task is None:
            return
        task_window_preset = task.window_preset

    with session_factory() as session:
        with session.begin():
            items = list(
                session.scalars(
                    select(TaskItem)
                    .where(
                        TaskItem.task_id == task_id,
                        TaskItem.status == TaskStatus.RUNNING.value,
                    )
                    .order_by(TaskItem.item_id.asc())
                ).all()
            )

    current_node: CurrentNode | None = None
    current_item_id: str | None = None
    try:
        for item in items:
            current_item_id = item.item_id
            request_url = _request_url(item.asin)
            node_id, node_name = _PIPELINE_NODES[0]

            with session_factory() as session:
                with session.begin():
                    _raise_if_cancel_requested(session, task_id)
                    started_at = _start_node(
                        session,
                        task_id=task_id,
                        item_id=item.item_id,
                        node_id=node_id,
                        node_name=node_name,
                    )
            current_node = (item.item_id, node_id, node_name, started_at)

            try:
                page = _fetch_page(fetcher, request_url)
            except Exception as exc:
                raise _PipelineFailure(
                    _task_error(
                        "FETCH_FAILED",
                        f"{type(exc).__name__}: {exc}",
                        retryable=True,
                    )
                ) from exc

            try:
                classification = _classify_page(page, requested_asin=item.asin)
            except Exception as exc:
                raise _PipelineFailure(
                    _task_error(
                        "PAGE_CLASSIFICATION_FAILED",
                        f"{type(exc).__name__}: {exc}",
                        retryable=True,
                    )
                ) from exc
            if page.http_status >= 400:
                raise _PipelineFailure(
                    _task_error(
                        "HTTP_ERROR",
                        f"Amazon returned HTTP {page.http_status} for {request_url}",
                        retryable=True,
                    )
                )
            if classification in {"BOT_CHECK", "SIGNIN"}:
                raise _PipelineFailure(
                    _task_error(
                        "PAGE_BLOCKED",
                        f"Amazon page blocked review extraction: {classification}",
                        retryable=True,
                    )
                )

            reviews, excluded_review_count = _extract_reviews(page.dom)
            for r in reviews:
                r["evidence_id"] = _new_id("evd")
            valid_review_count = len(reviews)
            raw_review_count = valid_review_count + excluded_review_count
            missing_reasons = ["NO_RAW_REVIEWS"] if raw_review_count == 0 else []
            sample_metrics = _sample_metrics(
                window_preset=task_window_preset,
                reviews=reviews,
                excluded_review_count=excluded_review_count,
                missing_reasons=missing_reasons,
            )
            warnings: list[dict[str, Any]] = (
                [
                    {
                        "code": "NO_RAW_REVIEWS",
                        "message": (
                            "Amazon 商品页未返回可验证的原始评论文本；"
                            "未使用 Customers say 摘要替代证据。"
                        ),
                        "related_item_id": item.item_id,
                        "evidence_refs": None,
                    }
                ]
                if raw_review_count == 0
                else []
            )
            data_quality = (
                DataQuality.NO_DATA if raw_review_count == 0 else DataQuality.SUFFICIENT
            )
            model_metadata: dict[str, Any] = {
                "engine": "insightx_analysis_engine",
                "models": (
                    []
                    if raw_review_count == 0
                    else ["semantic_clustering", "dual_column_proposal_mapper"]
                ),
                "model_skip_reason": "NO_RAW_REVIEWS" if raw_review_count == 0 else None,
                "capture": {
                    "request_url": request_url,
                    "final_url": page.final_url,
                    "http_status": page.http_status,
                    "page_classification": classification,
                    "extracted_review_count": raw_review_count,
                },
            }
            pain_points: list[ReportPainPoint] = []
            proposals: list[ReportProposal] = []

            with session_factory() as session:
                with session.begin():
                    _raise_if_cancel_requested(session, task_id)
                    _finish_node(
                        session,
                        task_id=task_id,
                        item_id=item.item_id,
                        node_id=node_id,
                        node_name=node_name,
                        status=NodeStatus.SUCCESS,
                        started_at=current_node[3],
                        details={
                            "request_url": request_url,
                            "final_url": page.final_url,
                            "http_status": page.http_status,
                            "extracted_review_count": raw_review_count,
                            "page_classification": classification,
                        },
                    )
                    current_node = None

                    if raw_review_count == 0:
                        for skipped_id, skipped_name, reason in (
                            (
                                "clean_and_embed",
                                "评论文本清洗与向量化",
                                "NO_RAW_REVIEWS",
                            ),
                            (
                                "cluster_pain_points",
                                "高频痛点聚类",
                                "NO_VALID_REVIEWS",
                            ),
                            (
                                "generate_proposals",
                                "生成双栏改款建议",
                                "NO_PAIN_POINTS",
                            ),
                        ):
                            skipped_started_at = utc_now()
                            _finish_node(
                                session,
                                task_id=task_id,
                                item_id=item.item_id,
                                node_id=skipped_id,
                                node_name=skipped_name,
                                status=NodeStatus.SKIPPED,
                                started_at=skipped_started_at,
                                skip_reason=reason,
                            )
                    else:
                        node_id, node_name = _PIPELINE_NODES[1]
                        started_at = _start_node(
                            session,
                            task_id=task_id,
                            item_id=item.item_id,
                            node_id=node_id,
                            node_name=node_name,
                        )
                        current_node = (item.item_id, node_id, node_name, started_at)
                        _finish_node(
                            session,
                            task_id=task_id,
                            item_id=item.item_id,
                            node_id=node_id,
                            node_name=node_name,
                            status=NodeStatus.SUCCESS,
                            started_at=current_node[3],
                            details={"valid_review_count": valid_review_count},
                        )
                        current_node = None

                        # Node 2: Cluster Pain Points
                        node_id, node_name = _PIPELINE_NODES[2]
                        started_at = _start_node(
                            session,
                            task_id=task_id,
                            item_id=item.item_id,
                            node_id=node_id,
                            node_name=node_name,
                        )
                        current_node = (item.item_id, node_id, node_name, started_at)
                        from insightx.services.analysis import analyze_reviews

                        evidence_ids = [r["evidence_id"] for r in reviews]
                        pain_points, proposals, data_quality, sample_metrics = (
                            analyze_reviews(
                                reviews,
                                evidence_ids=evidence_ids,
                                window_preset=task_window_preset,
                                excluded_count=excluded_review_count,
                            )
                        )
                        _finish_node(
                            session,
                            task_id=task_id,
                            item_id=item.item_id,
                            node_id=node_id,
                            node_name=node_name,
                            status=NodeStatus.SUCCESS,
                            started_at=current_node[3],
                            details={"pain_point_count": len(pain_points)},
                        )
                        current_node = None

                        # Node 3: Generate Proposals
                        node_id, node_name = _PIPELINE_NODES[3]
                        started_at = _start_node(
                            session,
                            task_id=task_id,
                            item_id=item.item_id,
                            node_id=node_id,
                            node_name=node_name,
                        )
                        current_node = (item.item_id, node_id, node_name, started_at)
                        _finish_node(
                            session,
                            task_id=task_id,
                            item_id=item.item_id,
                            node_id=node_id,
                            node_name=node_name,
                            status=NodeStatus.SUCCESS,
                            started_at=current_node[3],
                            details={"proposal_count": len(proposals)},
                        )
                        current_node = None

                    node_id, node_name = _PIPELINE_NODES[4]
                    started_at = _start_node(
                        session,
                        task_id=task_id,
                        item_id=item.item_id,
                        node_id=node_id,
                        node_name=node_name,
                    )
                    current_node = (item.item_id, node_id, node_name, started_at)

            with session_factory() as session:
                with session.begin():
                    _raise_if_cancel_requested(session, task_id)
                    task_row = session.get(Task, task_id)
                    item_row = session.get(TaskItem, item.item_id)
                    if task_row is None or item_row is None:
                        raise _PipelineFailure(
                            _task_error(
                                "PERSISTENCE_TARGET_MISSING",
                                "Task or item disappeared before report persistence.",
                                retryable=False,
                            )
                        )
                    _replace_evidence(
                        session,
                        task=task_row,
                        item=item_row,
                        reviews=reviews,
                        request_url=request_url,
                        final_url=page.final_url,
                        page_classification=classification,
                    )
                    _persist_report(
                        session,
                        task=task_row,
                        item=item_row,
                        sample_metrics=sample_metrics,
                        warnings=warnings,
                        model_metadata=model_metadata,
                        data_quality=data_quality,
                        pain_points=pain_points,
                        proposals=proposals,
                    )
                    _finish_node(
                        session,
                        task_id=task_id,
                        item_id=item.item_id,
                        node_id=node_id,
                        node_name=node_name,
                        status=NodeStatus.SUCCESS,
                        started_at=current_node[3],
                        details={
                            "data_quality": data_quality.value,
                            "evidence_count": valid_review_count,
                        },
                    )
                    current_node = None
                    _emit_event(
                        session,
                        task_id=task_id,
                        event_type="task_item.status_changed",
                        payload={"status": TaskStatus.COMPLETED.value},
                        task_item_id=item.item_id,
                    )

        with session_factory() as session:
            with session.begin():
                task_row = session.get(Task, task_id)
                if task_row is None:
                    return
                if task_row.cancel_requested_at is not None:
                    _cancel_task(
                        session,
                        task=task_row,
                        current_node=None,
                        outbox_message_id=outbox_message_id,
                        now=utc_now(),
                    )
                else:
                    _complete_task(
                        session,
                        task=task_row,
                        outbox_message_id=outbox_message_id,
                    )
    except _CancellationRequested:
        with session_factory() as session:
            with session.begin():
                task_row = session.get(Task, task_id)
                if task_row is None:
                    return
                if current_node is not None:
                    _cancel_current_item(
                        session,
                        task_id=task_id,
                        current_node=current_node,
                        outbox_message_id=outbox_message_id,
                    )
                else:
                    _cancel_task(
                        session,
                        task=task_row,
                        current_node=None,
                        outbox_message_id=outbox_message_id,
                        now=utc_now(),
                    )
    except _PipelineFailure as exc:
        node_id, node_name = (
            (current_node[1], current_node[2])
            if current_node is not None
            else ("pipeline", "任务执行")
        )
        logger.error("Task %s failed during %s: %s", task_id, node_id, exc)
        _fail_task(
            session_factory,
            task_id=task_id,
            error=exc.error,
            node_id=node_id,
            node_name=node_name,
            item_id=current_node[0] if current_node is not None else current_item_id,
            started_at=current_node[3] if current_node is not None else None,
            outbox_message_id=outbox_message_id,
            emit_node=current_node is not None,
        )
    except Exception as exc:
        node_id, node_name = (
            (current_node[1], current_node[2])
            if current_node is not None
            else ("pipeline", "任务执行")
        )
        error = _task_error(
            "WORKER_FAILED",
            f"{type(exc).__name__}: {exc}",
            retryable=True,
        )
        logger.exception("Task %s failed during %s", task_id, node_id)
        _fail_task(
            session_factory,
            task_id=task_id,
            error=error,
            node_id=node_id,
            node_name=node_name,
            item_id=current_node[0] if current_node is not None else current_item_id,
            started_at=current_node[3] if current_node is not None else None,
            outbox_message_id=outbox_message_id,
            emit_node=current_node is not None,
        )


def poll_and_execute_next(
    session_factory: SessionFactory,
    *,
    fetcher: Fetcher = fetch_dom,
    worker_id: str | None = None,
) -> bool:
    """Claim one transactional outbox message and process its task."""

    claimed = _claim_next_outbox(
        session_factory,
        worker_id=worker_id or _worker_id(),
    )
    if claimed is None:
        return False
    task_id, outbox_message_id = claimed
    execute_task_pipeline(
        session_factory,
        task_id,
        fetcher=fetcher,
        outbox_message_id=outbox_message_id,
    )
    return True


def run_worker(
    session_factory: SessionFactory,
    *,
    poll_interval: float = 1.0,
    run_once: bool = False,
    fetcher: Fetcher = fetch_dom,
) -> None:
    """Run persistent outbox polling worker loop."""

    logger.info("InsightX worker polling started.")
    while True:
        try:
            executed = poll_and_execute_next(session_factory, fetcher=fetcher)
            if run_once:
                break
            if not executed:
                time.sleep(poll_interval)
        except Exception:
            logger.exception("Error in worker loop")
            if run_once:
                raise
            time.sleep(poll_interval)
