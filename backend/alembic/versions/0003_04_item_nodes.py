"""阶段 04 节点执行记录表。

Revision ID: 0003_04_item_nodes — 显式 DDL，只追加，不改历史迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0003_04_item_nodes"
down_revision: str | None = "0002_03_task_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "item_nodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("task_items.id"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("node", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("output_version", sa.String(32), nullable=False),
        sa.Column("output_summary", sa.JSON(), nullable=True),
        sa.Column("skip_reason", sa.String(256), nullable=True),
        sa.UniqueConstraint(
            "item_id",
            "attempt",
            "node",
            "output_version",
            name="uq_item_nodes_item_attempt_node_version",
        ),
        sa.Index("ix_item_nodes_item_id", "item_id"),
    )


def downgrade() -> None:
    op.drop_table("item_nodes")
