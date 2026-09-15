"""Unit tests for background pipeline worker."""

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(BigInteger, "sqlite")
def compile_bigint_sqlite(type_, compiler, **kw):
    return "INTEGER"

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
from insightx.services.worker import execute_task_pipeline, poll_and_execute_next


@pytest.fixture
def sqlite_session_factory():
    """In-memory SQLite session factory with all tables."""
    engine = create_engine("sqlite:///:memory:")
    # Replace postgres-specific JSONB with standard JSON for sqlite tests
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


def test_worker_executes_pipeline(sqlite_session_factory):
    with sqlite_session_factory() as session:
        task = Task(
            task_id="tsk_test_1",
            tenant_id="dev-tenant",
            platform="amazon",
            marketplace="US",
            window_preset="1m",
            status=TaskStatus.QUEUED.value,
        )
        item = TaskItem(
            item_id="itm_test_1",
            task_id="tsk_test_1",
            tenant_id="dev-tenant",
            asin="B0FFW9LG7S",
            status=TaskStatus.QUEUED.value,
        )
        outbox = OutboxMessage(
            message_id="msg_test_1",
            tenant_id="dev-tenant",
            topic="task.created",
            aggregate_id="tsk_test_1",
            payload={"task_id": "tsk_test_1"},
            status="PENDING",
        )
        session.add_all([task, item, outbox])
        session.commit()

    # Execute pipeline
    execute_task_pipeline(sqlite_session_factory, "tsk_test_1")

    # Verify task completed
    with sqlite_session_factory() as session:
        completed_task = session.get(Task, "tsk_test_1")
        assert completed_task.status == TaskStatus.COMPLETED.value
        assert completed_task.finished_at is not None

        completed_item = session.get(TaskItem, "itm_test_1")
        assert completed_item.status == TaskStatus.COMPLETED.value
        assert completed_item.data_quality == "SUFFICIENT"
        assert completed_item.sample_metrics is not None

        # Verify Report exists
        report = session.query(Report).filter_by(task_id="tsk_test_1").first()
        assert report is not None
        assert len(report.pain_points) == 4
        assert len(report.proposals) == 4

        # Verify Evidence exists
        evidence_list = session.query(Evidence).filter_by(task_id="tsk_test_1").all()
        assert len(evidence_list) == 4

        # Verify Evidence Claim Refs exist
        claim_refs = session.query(EvidenceClaimRef).all()
        assert len(claim_refs) == 4

        # Verify Outbox Message published
        msg = session.get(OutboxMessage, "msg_test_1")
        assert msg.status == "PUBLISHED"

        # Verify Node Progress events
        node_events = (
            session.query(TaskEvent)
            .filter_by(task_id="tsk_test_1", event_type="task_item.node_progress")
            .all()
        )
        assert len(node_events) >= 10  # RUNNING and SUCCESS for each of the 5 nodes
