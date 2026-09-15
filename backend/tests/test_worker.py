"""Offline tests for the transactional background pipeline worker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import pytest
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from insightx.crawler.dom import DomNode
from insightx.crawler.fetch import FetchedPage
from insightx.database import Base
from insightx.models import (
    Evidence,
    EvidenceClaimRef,
    OutboxMessage,
    Report,
    Task,
    TaskEvent,
    TaskItem,
)
from insightx.schemas import NodeStatus, TaskStatus
from insightx.services.worker import poll_and_execute_next


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    """Render PostgreSQL JSONB as SQLite JSON for offline worker tests."""

    del type_, compiler, kw
    return "JSON"


@compiles(BigInteger, "sqlite")
def compile_bigint_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    """Render PostgreSQL BigInteger identity columns for SQLite."""

    del type_, compiler, kw
    return "INTEGER"


@pytest.fixture
def sqlite_session_factory():
    """Share one in-memory SQLite database across worker sessions."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_task(
    session_factory: sessionmaker[Session],
    *,
    task_id: str = "tsk_worker_test",
    item_id: str = "itm_worker_test",
    message_id: str = "msg_worker_test",
    status: TaskStatus = TaskStatus.QUEUED,
    outbox_status: str = "PENDING",
    locked_at: datetime | None = None,
    attempts: int = 0,
) -> None:
    now = datetime.now(UTC)
    with session_factory() as session:
        session.add_all(
            [
                Task(
                    task_id=task_id,
                    tenant_id="dev-tenant",
                    platform="amazon",
                    marketplace="US",
                    window_preset="6m",
                    status=status.value,
                ),
                TaskItem(
                    item_id=item_id,
                    task_id=task_id,
                    tenant_id="dev-tenant",
                    asin="B0FFWCNZGF",
                    status=status.value,
                ),
                OutboxMessage(
                    message_id=message_id,
                    tenant_id="dev-tenant",
                    topic="task.created",
                    aggregate_id=task_id,
                    payload={"task_id": task_id},
                    status=outbox_status,
                    attempts=attempts,
                    locked_by="dead-worker" if locked_at else None,
                    locked_at=locked_at,
                    created_at=now,
                    available_at=now,
                ),
            ]
        )
        session.commit()


def _empty_product_dom() -> DomNode:
    return {
        "type": "element",
        "tag": "html",
        "attributes": {},
        "children": [
            {
                "type": "element",
                "tag": "body",
                "attributes": {},
                "children": [
                    {
                        "type": "text",
                        "text": "4.3 out of 5 stars 382 global ratings",
                    }
                ],
            }
        ],
    }


def _empty_product_page(
    url: str,
    *,
    timeout_ms: int,
    headless: bool,
) -> FetchedPage:
    del timeout_ms, headless
    return FetchedPage(
        source_url=url,
        final_url="https://www.amazon.com/dp/B0FFWGQHJP?th=1&psc=1",
        title="Amazon product",
        http_status=200,
        captured_at=datetime.now(UTC),
        dom=_empty_product_dom(),
    )


def _node_statuses(session: Session, task_id: str) -> dict[str, str]:
    final: dict[str, str] = {}
    events = session.scalars(
        select(TaskEvent)
        .where(
            TaskEvent.task_id == task_id,
            TaskEvent.event_type == "task_item.node_progress",
        )
        .order_by(TaskEvent.event_id.asc())
    ).all()
    for event in events:
        final[str(event.payload["node_id"])] = str(event.payload["status"])
    return final


@pytest.mark.asyncio
async def test_poll_executes_no_data_report_and_publishes_outbox(
    sqlite_session_factory,
) -> None:
    _seed_task(sqlite_session_factory)
    calls: list[tuple[str, int, bool]] = []

    async def fake_fetcher(
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage:
        calls.append((url, timeout_ms, headless))
        return _empty_product_page(url, timeout_ms=timeout_ms, headless=headless)

    assert await _poll(sqlite_session_factory, fake_fetcher, "worker-1") is True
    assert calls == [
        ("https://www.amazon.com/dp/B0FFWCNZGF?th=1&psc=1", 45000, True)
    ]

    with sqlite_session_factory() as session:
        task = session.get(Task, "tsk_worker_test")
        item = session.get(TaskItem, "itm_worker_test")
        message = session.get(OutboxMessage, "msg_worker_test")
        report = session.scalar(
            select(Report).where(Report.task_id == "tsk_worker_test")
        )

        assert task is not None and task.status == TaskStatus.COMPLETED.value
        assert task.finished_at is not None
        assert item is not None
        assert item.status == TaskStatus.COMPLETED.value
        assert item.current_node is None
        assert item.data_quality == "NO_DATA"
        assert item.error is None
        assert item.sample_metrics == {
            "raw_review_count": 0,
            "valid_review_count": 0,
            "excluded_review_count": 0,
            "average_rating": None,
            "negative_review_ratio": None,
            "pain_point_count_with_evidence": 0,
            "window": {"preset": "6m"},
            "methodology": (
                "Amazon US 商品页 DOM 抽取、文本去噪与确定性统计；"
                "未调用嵌入或聚类模型，不生成无证据痛点。"
            ),
            "missing_reasons": ["NO_RAW_REVIEWS"],
        }
        assert report is not None
        assert report.data_quality == "NO_DATA"
        assert report.financial_state == "NOT_EVALUATED"
        assert report.pain_points == []
        assert report.proposals == []
        assert report.warnings == [
            {
                "code": "NO_RAW_REVIEWS",
                "message": (
                    "Amazon 商品页未返回可验证的原始评论文本；"
                    "未使用 Customers say 摘要替代证据。"
                ),
                "related_item_id": "itm_worker_test",
                "evidence_refs": None,
            }
        ]
        assert report.model_metadata["capture"] == {
            "request_url": "https://www.amazon.com/dp/B0FFWCNZGF?th=1&psc=1",
            "final_url": "https://www.amazon.com/dp/B0FFWGQHJP?th=1&psc=1",
            "http_status": 200,
            "page_classification": "PRODUCT_PAGE_VARIANT_REDIRECT",
            "extracted_review_count": 0,
        }
        assert session.scalar(select(Evidence)) is None
        assert session.scalar(select(EvidenceClaimRef)) is None
        assert message is not None
        assert message.status == "PUBLISHED"
        assert message.attempts == 1
        assert message.locked_by is None
        assert message.locked_at is None
        assert message.published_at is not None

        assert _node_statuses(session, "tsk_worker_test") == {
            "fetch_metadata": NodeStatus.SUCCESS.value,
            "clean_and_embed": NodeStatus.SKIPPED.value,
            "cluster_pain_points": NodeStatus.SKIPPED.value,
            "generate_proposals": NodeStatus.SKIPPED.value,
            "build_report": NodeStatus.SUCCESS.value,
        }

    assert await _poll(sqlite_session_factory, fake_fetcher, "worker-1") is False


@pytest.mark.asyncio
async def test_poll_reclaims_expired_outbox_lease(
    sqlite_session_factory,
) -> None:
    _seed_task(
        sqlite_session_factory,
        locked_at=datetime.now(UTC) - timedelta(minutes=5),
        attempts=2,
    )

    async def fake_fetcher(
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage:
        return _empty_product_page(url, timeout_ms=timeout_ms, headless=headless)

    assert await _poll(sqlite_session_factory, fake_fetcher, "worker-2") is True

    with sqlite_session_factory() as session:
        message = session.get(OutboxMessage, "msg_worker_test")
        assert message is not None
        assert message.status == "PUBLISHED"
        assert message.attempts == 3


@pytest.mark.asyncio
async def test_fetch_failure_is_terminal_and_clears_running_state(
    sqlite_session_factory,
) -> None:
    _seed_task(sqlite_session_factory)

    async def failing_fetcher(
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage:
        del url, timeout_ms, headless
        raise RuntimeError("browser unavailable")

    assert await _poll(sqlite_session_factory, failing_fetcher, "worker-3") is True

    with sqlite_session_factory() as session:
        task = session.get(Task, "tsk_worker_test")
        item = session.get(TaskItem, "itm_worker_test")
        message = session.get(OutboxMessage, "msg_worker_test")
        assert task is not None and task.status == TaskStatus.FAILED.value
        assert task.finished_at is not None
        assert item is not None
        assert item.status == TaskStatus.FAILED.value
        assert item.current_node is None
        assert item.error == {
            "code": "FETCH_FAILED",
            "message": "RuntimeError: browser unavailable",
            "retryable": True,
        }
        assert message is not None
        assert message.status == "PUBLISHED"
        assert _node_statuses(session, "tsk_worker_test") == {
            "fetch_metadata": NodeStatus.FAILED.value
        }


@pytest.mark.asyncio
async def test_cancellation_during_fetch_clears_state_without_fk_error(
    sqlite_session_factory,
) -> None:
    _seed_task(sqlite_session_factory)

    async def cancel_during_fetch(
        url: str,
        *,
        timeout_ms: int,
        headless: bool,
    ) -> FetchedPage:
        del timeout_ms, headless
        with sqlite_session_factory() as session:
            task = session.get(Task, "tsk_worker_test")
            assert task is not None
            task.cancel_requested_at = datetime.now(UTC)
            session.commit()
        return _empty_product_page(url, timeout_ms=45000, headless=True)

    assert await _poll(sqlite_session_factory, cancel_during_fetch, "worker-4") is True

    with sqlite_session_factory() as session:
        task = session.get(Task, "tsk_worker_test")
        item = session.get(TaskItem, "itm_worker_test")
        message = session.get(OutboxMessage, "msg_worker_test")
        assert task is not None and task.status == TaskStatus.CANCELED.value
        assert item is not None
        assert item.status == TaskStatus.CANCELED.value
        assert item.current_node is None
        assert message is not None and message.status == "PUBLISHED"
        assert _node_statuses(session, "tsk_worker_test") == {
            "fetch_metadata": NodeStatus.CANCELED.value
        }
        assert session.scalar(select(Report)) is None


async def _poll(
    session_factory: sessionmaker[Session],
    fetcher: Any,
    worker_id: str,
) -> bool:
    """Run one poll without invoking the sync worker CLI event loop wrapper."""

    del _poll
    raise AssertionError("unreachable")


def _expected_request_host(url: str) -> str:
    return urlparse(url).hostname or ""
