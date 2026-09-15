"""Create the P0 task API persistence tables.

Revision ID: 20260914_task_api_base
Revises:
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260914_task_api_base"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("parent_task_id", sa.String(length=64), nullable=True),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("marketplace", sa.String(length=16), nullable=False),
        sa.Column("window_preset", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_task_id"],
            ["tasks.task_id"],
            name="tasks_parent_task_id_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index(
        "ix_tasks_tenant_created_task",
        "tasks",
        ["tenant_id", "created_at", "task_id"],
        unique=False,
    )

    op.create_table(
        "task_items",
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("asin", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_node", sa.String(length=128), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("data_quality", sa.String(length=32), nullable=True),
        sa.Column(
            "sample_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.task_id"],
            name="task_items_task_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("item_id"),
        sa.UniqueConstraint("task_id", "asin", name="uq_task_items_task_asin"),
    )
    op.create_index(
        "ix_task_items_tenant_task",
        "task_items",
        ["tenant_id", "task_id"],
        unique=False,
    )

    op.create_table(
        "task_events",
        sa.Column(
            "event_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("task_item_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.task_id"],
            name="task_events_task_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_item_id"],
            ["task_items.item_id"],
            name="task_events_task_item_id_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_task_events_task_event",
        "task_events",
        ["task_id", "event_id"],
        unique=False,
    )
    op.create_index(
        "ix_task_events_task_item_event",
        "task_events",
        ["task_item_id", "event_id"],
        unique=False,
    )

    op.create_table(
        "reports",
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("data_quality", sa.String(length=32), nullable=False),
        sa.Column(
            "sample_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("financial_state", sa.String(length=32), nullable=False),
        sa.Column(
            "pain_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("proposals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "model_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["task_items.item_id"],
            name="reports_item_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.task_id"],
            name="reports_task_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("report_id"),
        sa.UniqueConstraint("task_id", "item_id", name="uq_reports_task_item"),
    )
    op.create_index(
        "ix_reports_tenant_task_item",
        "reports",
        ["tenant_id", "task_id", "item_id"],
        unique=False,
    )

    op.create_table(
        "evidence",
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=256), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["task_items.item_id"],
            name="evidence_item_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.task_id"],
            name="evidence_task_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("evidence_id"),
    )
    op.create_index(
        "ix_evidence_tenant_source_type",
        "evidence",
        ["tenant_id", "source_type"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_tenant_task_item_created",
        "evidence",
        ["tenant_id", "task_id", "item_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "evidence_claim_refs",
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("claim_type", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            name="evidence_claim_refs_evidence_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("evidence_id", "claim_id"),
    )
    op.create_index(
        "ix_evidence_claim_refs_claim",
        "evidence_claim_refs",
        ["claim_id", "evidence_id"],
        unique=False,
    )

    op.create_table(
        "idempotency_records",
        sa.Column("record_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=256), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("record_id"),
        sa.UniqueConstraint(
            "tenant_id", "scope", "key", name="uq_idempotency_tenant_scope_key"
        ),
    )

    op.create_table(
        "outbox_messages",
        sa.Column("message_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("topic", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.create_index(
        "ix_outbox_messages_status_available",
        "outbox_messages",
        ["status", "available_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_messages_status_available", table_name="outbox_messages")
    op.drop_table("outbox_messages")
    op.drop_table("idempotency_records")
    op.drop_index("ix_evidence_claim_refs_claim", table_name="evidence_claim_refs")
    op.drop_table("evidence_claim_refs")
    op.drop_index("ix_evidence_tenant_task_item_created", table_name="evidence")
    op.drop_index("ix_evidence_tenant_source_type", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_reports_tenant_task_item", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_task_events_task_item_event", table_name="task_events")
    op.drop_index("ix_task_events_task_event", table_name="task_events")
    op.drop_table("task_events")
    op.drop_index("ix_task_items_tenant_task", table_name="task_items")
    op.drop_table("task_items")
    op.drop_index("ix_tasks_tenant_created_task", table_name="tasks")
    op.drop_table("tasks")
