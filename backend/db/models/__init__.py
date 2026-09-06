"""SQLAlchemy ORM models for the InsightX domain (docs/04-技术方案 §3.2)."""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db.base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


JsonDict = JSON


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = _uuid_pk()
    asin: Mapped[str] = mapped_column(String(32), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="amazon")
    marketplace: Mapped[str] = mapped_column(String(16), nullable=False, default="US")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(128))
    current_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    main_image_url: Mapped[str | None] = mapped_column(Text)
    length_cm: Mapped[float | None] = mapped_column(Numeric(8, 2))
    width_cm: Mapped[float | None] = mapped_column(Numeric(8, 2))
    height_cm: Mapped[float | None] = mapped_column(Numeric(8, 2))
    weight_kg: Mapped[float | None] = mapped_column(Numeric(8, 2))
    bsr: Mapped[int | None] = mapped_column(Integer)
    bsr_category: Mapped[str | None] = mapped_column(String(128))
    review_count: Mapped[int | None] = mapped_column(Integer)
    avg_rating: Mapped[float | None] = mapped_column(Numeric(3, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("uk_product_platform", "asin", "platform", "marketplace", unique=True),
    )


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = _uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    external_review_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    review_date: Mapped[str | None] = mapped_column(String(16))
    original_language: Mapped[str] = mapped_column(String(16), default="en")
    title: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    translated_content: Mapped[str | None] = mapped_column(Text)
    verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False)
    helpful_votes: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))  # bge-m3 dense vector
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("uk_review_external", "product_id", "external_review_id", unique=True),
        Index("idx_reviews_product_rating", "product_id", "rating"),
    )

    images: Mapped[list["ReviewImage"]] = relationship(back_populates="review", cascade="all, delete-orphan")


class ReviewImage(Base):
    __tablename__ = "review_images"

    id: Mapped[uuid.UUID] = _uuid_pk()
    review_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    defect_type: Mapped[str | None] = mapped_column(String(64))
    vlm_analysis: Mapped[dict[str, Any] | None] = mapped_column(JsonDict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    review: Mapped[Review] = relationship(back_populates="images")


class InsightTaskModel(Base):
    __tablename__ = "insight_tasks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    asin: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    platform: Mapped[str] = mapped_column(String(32), default="amazon")
    marketplace: Mapped[str] = mapped_column(String(16), default="US")
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    current_node: Mapped[str | None] = mapped_column(String(64))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    review_window_months: Mapped[int] = mapped_column(Integer, default=6)
    max_reviews: Mapped[int] = mapped_column(Integer, default=500)
    financial_constraint: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=dict)
    options: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=dict)
    final_report: Mapped[dict[str, Any] | None] = mapped_column(JsonDict)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClusterModel(Base):
    __tablename__ = "clusters"

    id: Mapped[uuid.UUID] = _uuid_pk()
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(64), nullable=False)
    cluster_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, default=0)
    frequency_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    severity_score: Mapped[float] = mapped_column(Float, default=0.0)
    severity_level: Mapped[str] = mapped_column(String(16), default="minor")
    keywords: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    sample_quotes: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    sample_image_ids: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    review_ids: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("uk_cluster_task", "task_id", "cluster_id", unique=True),)


class ReformProposalModel(Base):
    __tablename__ = "reform_proposals"

    id: Mapped[uuid.UUID] = _uuid_pk()
    proposal_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    track_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cost_estimation_usd: Mapped[float | None] = mapped_column(Numeric(10, 2))
    mold_opening_required: Mapped[bool] = mapped_column(Boolean, default=False)
    mold_cycle_days: Mapped[int] = mapped_column(Integer, default=0)
    estimated_roi: Mapped[float | None] = mapped_column(Numeric(5, 2))
    defect_rate_reduction: Mapped[float | None] = mapped_column(Numeric(5, 2))
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    veto_reason: Mapped[str | None] = mapped_column(Text)
    fallback_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    source_cluster_ids: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    evidence_review_ids: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    evidence_image_ids: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    packaging_meta: Mapped[dict[str, Any] | None] = mapped_column(JsonDict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FinancialResultModel(Base):
    __tablename__ = "financial_results"

    id: Mapped[uuid.UUID] = _uuid_pk()
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    veto_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    checked_proposals: Mapped[int] = mapped_column(Integer, default=0)
    vetoed_proposal_ids: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    veto_reasons: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    fallback_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    financial_constraint: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EvidenceLinkModel(Base):
    __tablename__ = "evidence_links"

    id: Mapped[uuid.UUID] = _uuid_pk()
    proposal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(64), nullable=False)
    review_ids: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    image_ids: Mapped[dict[str, Any]] = mapped_column(JsonDict, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
