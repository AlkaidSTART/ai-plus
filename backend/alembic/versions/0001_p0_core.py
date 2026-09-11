"""P0 闭环表初始建表（显式冻结）。

Revision ID: 0001_p0_core — 本文件是唯一真相源，不再从 ORM metadata 派生，
避免未来模型修改改变历史迁移行为。与 app.db.models 的结构一致性由
tests/test_migrations.py 在离线 SQL 层面核对。
P1/P2 表在对应阶段新增独立迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001_p0_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("marketplace", sa.String(16), nullable=False),
    )
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("marketplace", sa.String(16), nullable=False),
        sa.Column("asin", sa.String(32), nullable=False),
        sa.Column("parent_asin", sa.String(32), nullable=True),
        sa.UniqueConstraint(
            "tenant_id",
            "platform",
            "marketplace",
            "asin",
            name="uq_products_tenant_platform_marketplace_asin",
        ),
    )
    op.create_table(
        "memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
    )
    op.create_table(
        "product_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("bsr", sa.Integer(), nullable=True),
    )
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("phase", sa.String(8), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(128), nullable=False),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_tasks_tenant_idempotency_key",
        ),
        sa.Index(
            "ix_tasks_tenant_project_created_id",
            "tenant_id",
            "project_id",
            "created_at",
            "id",
        ),
    )
    op.create_table(
        "reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("source_review_id", sa.String(128), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("rating", sa.Numeric(2, 1), nullable=True),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("reviewed_at", sa.Date(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "product_id",
            "source_review_id",
            "content_hash",
            name="uq_reviews_product_source_hash",
        ),
        sa.Index(
            "ix_reviews_product_reviewed_id",
            "product_id",
            "reviewed_at",
            "id",
        ),
    )
    op.create_table(
        "data_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column(
            "product_snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("product_snapshots.id"),
            nullable=True,
        ),
        sa.Column("window_start", sa.Date(), nullable=True),
        sa.Column("window_end", sa.Date(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_query", sa.JSON(), nullable=False),
        sa.Column("cleaning_version", sa.String(32), nullable=False),
        sa.Column("coverage", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
    )
    op.create_table(
        "review_fragments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("review_id", UUID(as_uuid=True), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("start", sa.Integer(), nullable=False),
        sa.Column("end", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("extraction_version", sa.String(32), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("embedding_model_revision", sa.String(64), nullable=True),
    )
    op.create_table(
        "task_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("current_node", sa.String(64), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("lease_owner", sa.String(128), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_version", sa.Integer(), nullable=False),
        sa.Column(
            "snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("data_snapshots.id"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "task_id",
            "product_id",
            name="uq_task_items_task_product",
        ),
        sa.Index("ix_task_items_task_id", "task_id"),
    )
    op.create_table(
        "snapshot_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("data_snapshots.id"),
            nullable=False,
        ),
        sa.Column("review_id", UUID(as_uuid=True), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("included", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.String(128), nullable=True),
        sa.UniqueConstraint(
            "snapshot_id",
            "review_id",
            name="uq_snapshot_reviews_snapshot_review",
        ),
    )
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("task_items.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("data_snapshots.id"),
            nullable=False,
        ),
        sa.Column("pipeline_version", sa.String(32), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column("availability", sa.String(16), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "item_id",
            "version",
            name="uq_reports_item_version",
        ),
    )
    op.create_table(
        "task_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("task_items.id"),
            nullable=True,
        ),
        sa.Column("attempt", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "task_id",
            "seq",
            name="uq_task_events_task_seq",
        ),
    )
    op.create_table(
        "issue_clusters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("report_id", UUID(as_uuid=True), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("name_zh", sa.String(256), nullable=False),
        sa.Column("name_en", sa.String(256), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("denominator", sa.Integer(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("severity_reason", sa.Text(), nullable=False),
    )
    op.create_table(
        "reform_proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("report_id", UUID(as_uuid=True), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("column", sa.String(16), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("expected_effect", sa.Text(), nullable=False),
        sa.Column("verification_required", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
    )
    op.create_table(
        "cluster_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cluster_id",
            UUID(as_uuid=True),
            sa.ForeignKey("issue_clusters.id"),
            nullable=False,
        ),
        sa.Column(
            "fragment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("review_fragments.id"),
            nullable=False,
        ),
        sa.Column("relevance", sa.Numeric(5, 4), nullable=True),
        sa.UniqueConstraint(
            "cluster_id",
            "fragment_id",
            name="uq_cluster_members_cluster_fragment",
        ),
    )
    op.create_table(
        "proposal_issues",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "proposal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("reform_proposals.id"),
            nullable=False,
        ),
        sa.Column(
            "cluster_id",
            UUID(as_uuid=True),
            sa.ForeignKey("issue_clusters.id"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "proposal_id",
            "cluster_id",
            name="uq_proposal_issues_proposal_cluster",
        ),
    )


def downgrade() -> None:
    for table in (
        "proposal_issues",
        "cluster_members",
        "reform_proposals",
        "issue_clusters",
        "task_events",
        "reports",
        "snapshot_reviews",
        "task_items",
        "review_fragments",
        "data_snapshots",
        "reviews",
        "tasks",
        "product_snapshots",
        "memberships",
        "products",
        "projects",
        "users",
        "tenants",
    ):
        op.drop_table(table)
