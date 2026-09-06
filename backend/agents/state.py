"""Strongly typed LangGraph state for the InsightX workflow."""

from typing import Any, TypedDict


class ReviewItem(TypedDict):
    review_id: str
    asin: str
    rating: float
    review_date: str
    language: str
    title: str
    content: str
    translated_content: str | None
    verified_purchase: bool
    helpful_votes: int
    image_urls: list[str]


class VisualEvidence(TypedDict):
    image_id: str
    review_id: str
    storage_url: str
    defect_category: str  # color_difference | broken_package | craft_flaw | dimension_issue | other
    description: str
    confidence: float
    bbox: list[int]
    cluster_ids: list[str]


class ClusterItem(TypedDict):
    cluster_id: str
    cluster_name: str
    issue_type: str  # product_defect | function_defect | size_spec | accessory | manual | packaging_delivery | other
    frequency: int
    frequency_ratio: float
    severity_score: float
    severity_level: str  # critical | moderate | minor
    keywords: list[str]
    sample_quotes: list[dict[str, Any]]
    sample_image_ids: list[str]
    review_ids: list[str]


class ProposalItem(TypedDict, total=False):
    proposal_id: str
    task_id: str
    track_type: str  # BODY_OPTIMIZATION | PACKAGING_FULFILLMENT
    title: str
    description: str
    cost_estimation_usd: float
    mold_opening_required: bool
    mold_cycle_days: int
    estimated_roi: float
    defect_rate_reduction: float
    status: str  # PENDING | PASSED | VETOED
    veto_reason: str | None
    fallback_applied: bool
    source_cluster_ids: list[str]
    evidence_review_count: int
    evidence_image_count: int
    created_at: str

    # Packaging track extras (docs/api.md §8.2)
    package_size_old_cm: list[int]
    package_size_new_cm: list[int]
    volumetric_weight_old_kg: float
    volumetric_weight_new_kg: float
    fba_tier_old: str
    fba_tier_new: str
    fulfillment_saving_usd_per_unit: float


class EvidenceLinkItem(TypedDict):
    proposal_id: str
    cluster_id: str
    review_ids: list[str]
    image_ids: list[str]


class InsightState(TypedDict, total=False):
    # Identity
    task_id: str
    asin: str
    platform: str
    marketplace: str
    review_window_months: int
    max_reviews: int

    # Flow data
    raw_reviews: list[ReviewItem]
    visual_evidences: list[VisualEvidence]
    clustered_issues: list[ClusterItem]
    proposals: list[ProposalItem]

    # Configuration
    financial_constraint: dict[str, Any]
    options: dict[str, Any]

    # Decision / retry
    veto_status: str  # PENDING | PASSED | VETOED
    retry_count: int
    fallback_applied: bool

    # Progress tracking
    current_node: str
    progress: int

    # Traceability & outputs
    evidence_links: list[EvidenceLinkItem]
    backtest_score: float | None
    final_report: dict[str, Any]

    error_message: str | None
