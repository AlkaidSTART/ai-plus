"""P0 闭环表（技术方案 §4.1）。逻辑表设计，非业务逻辑；P1/P2 表在对应阶段新增迁移。

约束要点：企业业务表带 tenant_id；任务幂等键同租户唯一；事件 (task, seq) 唯一；
证据数量一律由 proposal→…→review 路径按 review 去重导出，不存快照计数。
连接表经父级外键链路归属租户，由应用层校验同报告/同任务边界（阶段 03/08 测试覆盖）。
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

UUID_PK = UUID(as_uuid=True)


def _uuid() -> Mapped[uuid.UUID]:
    return mapped_column(UUID_PK, primary_key=True, default=uuid.uuid4)


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = _uuid()
    name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = _now()


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    email: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = _now()


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(32), default="member")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    marketplace: Mapped[str] = mapped_column(String(16), default="US")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "platform",
            "marketplace",
            "asin",
            name="uq_products_tenant_platform_marketplace_asin",
        ),
    )
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    platform: Mapped[str] = mapped_column(String(32), default="amazon")
    marketplace: Mapped[str] = mapped_column(String(16), default="US")
    asin: Mapped[str] = mapped_column(String(32))
    parent_asin: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ProductSnapshot(Base):
    __tablename__ = "product_snapshots"
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    bsr: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_tasks_tenant_idempotency_key",
        ),
        Index(
            "ix_tasks_tenant_project_created_id",
            "tenant_id",
            "project_id",
            "created_at",
            "id",
        ),
    )
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    input: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="QUEUED")
    phase: Mapped[str] = mapped_column(String(8), default="P0")
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(128))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True
    )
    created_at: Mapped[datetime] = _now()


class TaskItem(Base):
    __tablename__ = "task_items"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "product_id",
            name="uq_task_items_task_product",
        ),
        Index("ix_task_items_task_id", "task_id"),
    )
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    status: Mapped[str] = mapped_column(String(16), default="QUEUED")
    current_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_version: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_snapshots.id"), nullable=True
    )
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DataSnapshot(Base):
    __tablename__ = "data_snapshots"
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    product_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_snapshots.id"), nullable=True
    )
    window_start: Mapped[Date | None] = mapped_column(Date, nullable=True)
    window_end: Mapped[Date | None] = mapped_column(Date, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(64))
    source_query: Mapped[dict] = mapped_column(JSON)
    cleaning_version: Mapped[str] = mapped_column(String(32))
    coverage: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(128))


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "source_review_id",
            "content_hash",
            name="uq_reviews_product_source_hash",
        ),
        Index(
            "ix_reviews_product_reviewed_id",
            "product_id",
            "reviewed_at",
            "id",
        ),
    )
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    source_review_id: Mapped[str] = mapped_column(String(128))
    content_hash: Mapped[str] = mapped_column(String(128))
    raw_text: Mapped[str] = mapped_column(Text)
    rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reviewed_at: Mapped[Date | None] = mapped_column(Date, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class SnapshotReview(Base):
    __tablename__ = "snapshot_reviews"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "review_id",
            name="uq_snapshot_reviews_snapshot_review",
        ),
    )
    id: Mapped[uuid.UUID] = _uuid()
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_snapshots.id"))
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reviews.id"))
    included: Mapped[bool] = mapped_column(Boolean, default=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ReviewFragment(Base):
    __tablename__ = "review_fragments"
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reviews.id"))
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    extraction_version: Mapped[str] = mapped_column(String(32))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    embedding_model_revision: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint(
            "item_id",
            "version",
            name="uq_reports_item_version",
        ),
    )
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_items.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_snapshots.id"))
    pipeline_version: Mapped[str] = mapped_column(String(32))
    model_version: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    availability: Mapped[str] = mapped_column(String(16))
    limitations: Mapped[list] = mapped_column(JSON)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IssueCluster(Base):
    __tablename__ = "issue_clusters"
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id"))
    name_zh: Mapped[str] = mapped_column(String(256))
    name_en: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(32))
    frequency: Mapped[int] = mapped_column(Integer)
    denominator: Mapped[int] = mapped_column(Integer)
    severity: Mapped[int] = mapped_column(Integer)
    severity_reason: Mapped[str] = mapped_column(Text)


class ClusterMember(Base):
    __tablename__ = "cluster_members"
    __table_args__ = (
        UniqueConstraint(
            "cluster_id",
            "fragment_id",
            name="uq_cluster_members_cluster_fragment",
        ),
    )
    id: Mapped[uuid.UUID] = _uuid()
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("issue_clusters.id"))
    fragment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("review_fragments.id"))
    relevance: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)


class ReformProposal(Base):
    __tablename__ = "reform_proposals"
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id"))
    column: Mapped[str] = mapped_column(String(16))  # PRODUCT / PACKAGING
    title: Mapped[str] = mapped_column(String(256))
    action: Mapped[str] = mapped_column(Text)
    expected_effect: Mapped[str] = mapped_column(Text)
    verification_required: Mapped[list] = mapped_column(JSON)
    assumptions: Mapped[list] = mapped_column(JSON)


class ProposalIssue(Base):
    __tablename__ = "proposal_issues"
    __table_args__ = (
        UniqueConstraint(
            "proposal_id",
            "cluster_id",
            name="uq_proposal_issues_proposal_cluster",
        ),
    )
    id: Mapped[uuid.UUID] = _uuid()
    proposal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reform_proposals.id"))
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("issue_clusters.id"))


class TaskEvent(Base):
    __tablename__ = "task_events"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "seq",
            name="uq_task_events_task_seq",
        ),
    )
    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"))
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(64))
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_items.id"), nullable=True
    )
    attempt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)


class ItemNode(Base):
    """分项节点执行记录（阶段 04）。幂等键覆盖 item/attempt/node/output_version。"""

    __tablename__ = "item_nodes"
    __table_args__ = (
        UniqueConstraint(
            "item_id",
            "attempt",
            "node",
            "output_version",
            name="uq_item_nodes_item_attempt_node_version",
        ),
        Index("ix_item_nodes_item_id", "item_id"),
    )
    id: Mapped[uuid.UUID] = _uuid()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_items.id"))
    attempt: Mapped[int] = mapped_column(Integer)
    node: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_version: Mapped[str] = mapped_column(String(32), default="v1")
    output_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    skip_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
