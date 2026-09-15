"""Persistence models for tasks, reports, evidence, and delivery state."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from insightx.database import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class Task(Base):
    """A batch diagnosis request and its lifecycle state."""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_tenant_created_task", "tenant_id", "created_at", "task_id"),
    )

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.task_id", ondelete="SET NULL"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    marketplace: Mapped[str] = mapped_column(String(16), nullable=False)
    window_preset: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TaskItem(Base):
    """One ASIN work item inside a task batch."""

    __tablename__ = "task_items"
    __table_args__ = (
        UniqueConstraint("task_id", "asin", name="uq_task_items_task_asin"),
        Index("ix_task_items_tenant_task", "tenant_id", "task_id"),
    )

    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    asin: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_node: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    data_quality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sample_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class TaskEvent(Base):
    """Append-only task event used for SSE replay."""

    __tablename__ = "task_events"
    __table_args__ = (
        Index("ix_task_events_task_event", "task_id", "event_id"),
        Index("ix_task_events_task_item_event", "task_item_id", "event_id"),
    )

    event_id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )
    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False
    )
    task_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("task_items.item_id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class Report(Base):
    """A generated diagnosis report for one task item."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("task_id", "item_id", name="uq_reports_task_item"),
        Index("ix_reports_tenant_task_item", "tenant_id", "task_id", "item_id"),
    )

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(
        ForeignKey("task_items.item_id", ondelete="CASCADE"), nullable=False
    )
    data_quality: Mapped[str] = mapped_column(String(32), nullable=False)
    sample_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    financial_state: Mapped[str] = mapped_column(String(32), nullable=False)
    pain_points: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    proposals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    model_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class Evidence(Base):
    """A text evidence record that can support report claims."""

    __tablename__ = "evidence"
    __table_args__ = (
        Index(
            "ix_evidence_tenant_task_item_created",
            "tenant_id",
            "task_id",
            "item_id",
            "created_at",
        ),
        Index("ix_evidence_tenant_source_type", "tenant_id", "source_type"),
    )

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(
        ForeignKey("task_items.item_id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class EvidenceClaimRef(Base):
    """Many-to-many mapping between evidence and report claims."""

    __tablename__ = "evidence_claim_refs"
    __table_args__ = (
        Index("ix_evidence_claim_refs_claim", "claim_id", "evidence_id"),
    )

    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence.evidence_id", ondelete="CASCADE"), primary_key=True
    )
    claim_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_type: Mapped[str] = mapped_column(String(32), nullable=False)


class IdempotencyRecord(Base):
    """Durable result for one tenant-scoped idempotent operation."""

    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "scope", "key", name="uq_idempotency_tenant_scope_key"
        ),
    )

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(256), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class OutboxMessage(Base):
    """Transactional outbox message awaiting future delivery."""

    __tablename__ = "outbox_messages"
    __table_args__ = (
        Index("ix_outbox_messages_status_available", "status", "available_at"),
    )

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
