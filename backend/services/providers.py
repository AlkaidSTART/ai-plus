"""Deterministic providers for the InsightX workflow (Step 2).

These providers emit fixed but structurally correct data so the LangGraph
state machine, runtime and SSE pipeline can be developed and tested offline.
Step 3 replaces each provider with a real implementation behind the same
interface — the graph is not touched.
"""

import hashlib
from typing import Any, Protocol

from agents.state import ClusterItem, EvidenceLinkItem, ProposalItem, ReviewItem, VisualEvidence
from services.financial import FinancialEngine, fba_tier_for, volumetric_weight_kg

DEFECT_SEEDS: list[tuple[str, str, str, str]] = [
    # (keyword, en text, cluster name, issue_type)
    ("broke", "The handle broke after one week of normal use.", "把手易断裂", "product_defect"),
    ("color", "The color looks different from the product pictures.", "实物色差明显", "product_defect"),
    ("crushed", "The box arrived crushed and the item was scratched.", "运输包装易破损", "packaging_delivery"),
    ("small", "Runs smaller than the described size, does not fit.", "尺寸偏小与描述不符", "size_spec"),
    ("missing", "Missing a screw in the package, cannot assemble.", "配件缺失", "accessory"),
]


class ReviewProvider(Protocol):
    async def fetch(
        self, asin: str, marketplace: str, window_months: int, max_reviews: int
    ) -> list[ReviewItem]: ...


class VisionProvider(Protocol):
    async def audit(self, reviews: list[ReviewItem]) -> list[VisualEvidence]: ...


class ClusterProvider(Protocol):
    async def cluster(
        self, task_id: str, reviews: list[ReviewItem], evidences: list[VisualEvidence]
    ) -> list[ClusterItem]: ...


class DecisionProvider(Protocol):
    async def decide(
        self,
        task_id: str,
        clusters: list[ClusterItem],
        constraint: dict[str, Any],
        retry_count: int,
    ) -> list[ProposalItem]: ...


class EvidenceProvider(Protocol):
    async def trace(
        self,
        task_id: str,
        proposals: list[ProposalItem],
        clusters: list[ClusterItem],
        evidences: list[VisualEvidence],
    ) -> list[EvidenceLinkItem]: ...


class BacktestProvider(Protocol):
    async def evaluate(
        self, task_id: str, clusters: list[ClusterItem]
    ) -> float: ...


class FinancialProvider(Protocol):
    engine: Any

    def evaluate_proposal(self, proposal: dict, constraint: dict) -> Any: ...

    async def record(
        self, task_id: str, proposals: list[ProposalItem],
        constraint: dict, retry_count: int,
    ) -> None: ...


def _seed(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


class DeterministicReviewProvider:
    """Generates a fixed set of realistic-looking reviews per ASIN."""

    async def fetch(
        self, asin: str, marketplace: str, window_months: int, max_reviews: int
    ) -> list[ReviewItem]:
        count = min(max_reviews, 40)
        reviews: list[ReviewItem] = []
        for i in range(count):
            seed = _seed(f"{asin}:{i}")
            if i % 5 == 4:
                # positive filler
                rating, text = 5.0, "Great product, works as expected."
            elif i % 7 == 3:
                # 无意义短评（上游真实存在的垃圾数据，供清洗管道过滤）
                rating, text = 4.0, ("ok", "Good", "Fast shipping", "Nice")[seed % 4]
            else:
                defect = DEFECT_SEEDS[seed % len(DEFECT_SEEDS)]
                rating, text = 1.0 + (seed % 3), defect[1]
            with_image = i % 4 == 0 and rating <= 2.0
            reviews.append(
                ReviewItem(
                    review_id=f"rev_{asin}_{i:04d}",
                    asin=asin,
                    rating=float(rating),
                    review_date=f"2026-0{(i % 6) + 1}-1{(i % 9)}",
                    language="en",
                    title=text[:40],
                    content=text,
                    translated_content=None,
                    verified_purchase=bool(seed % 2),
                    helpful_votes=seed % 30,
                    image_urls=[f"https://cdn.insightx.local/img/{asin}/{i}.jpg"]
                    if with_image
                    else [],
                )
            )
        return reviews


class DeterministicVisionProvider:
    async def audit(self, reviews: list[ReviewItem]) -> list[VisualEvidence]:
        evidences: list[VisualEvidence] = []
        for review in reviews:
            for j, url in enumerate(review["image_urls"]):
                seed = _seed(url)
                category = ["craft_flaw", "broken_package", "color_difference", "dimension_issue"][seed % 4]
                evidences.append(
                    VisualEvidence(
                        image_id=f"img_{review['review_id'][-4:]}_{j}",
                        review_id=review["review_id"],
                        storage_url=url,
                        defect_category=category,
                        description="实拍图可见明显缺陷，用于取证（deterministic provider）",
                        confidence=0.6 + (seed % 35) / 100,
                        bbox=[40 + seed % 50, 30, 300 + seed % 80, 260 + seed % 60],
                        cluster_ids=[],
                    )
                )
        return evidences


class DeterministicClusterProvider:
    async def cluster(
        self, task_id: str, reviews: list[ReviewItem], evidences: list[VisualEvidence]
    ) -> list[ClusterItem]:
        total = max(len(reviews), 1)
        clusters: list[ClusterItem] = []
        for idx, (keyword, _, name, issue_type) in enumerate(DEFECT_SEEDS):
            matched = [
                r for r in reviews if keyword in r["content"].lower() or keyword in r["title"].lower()
            ]
            if not matched:
                continue
            frequency = len(matched)
            ratio = round(frequency / total, 2)
            severity = round(min(5.0, 2.0 + ratio * 8), 1)
            cluster_id = f"clu_{idx + 1:02d}"
            clusters.append(
                ClusterItem(
                    cluster_id=cluster_id,
                    cluster_name=name,
                    issue_type=issue_type,
                    frequency=frequency,
                    frequency_ratio=ratio,
                    severity_score=severity,
                    severity_level="critical" if severity >= 4.0 else "moderate" if severity >= 2.5 else "minor",
                    keywords=[keyword],
                    sample_quotes=[
                        {
                            "review_id": r["review_id"],
                            "language": r["language"],
                            "content": r["content"],
                            "translated_content": r["translated_content"],
                            "rating": r["rating"],
                        }
                        for r in matched[:3]
                    ],
                    sample_image_ids=[
                        e["image_id"] for e in evidences if e["review_id"] in {m["review_id"] for m in matched}
                    ][:5],
                    review_ids=[r["review_id"] for r in matched],
                )
            )
        clusters.sort(key=lambda c: (c["severity_score"], c["frequency"]), reverse=True)
        return clusters[:5]


class DeterministicDecisionProvider:
    def __init__(self, engine: FinancialEngine | None = None) -> None:
        self._engine = engine or FinancialEngine()

    async def decide(
        self,
        task_id: str,
        clusters: list[ClusterItem],
        constraint: dict[str, Any],
        retry_count: int,
    ) -> list[ProposalItem]:
        proposals: list[ProposalItem] = []
        fallback = retry_count > 0
        body_clusters = [c for c in clusters if c["issue_type"] not in ("packaging_delivery",)]
        packaging_clusters = [c for c in clusters if c["issue_type"] == "packaging_delivery"]

        for i, cluster in enumerate(body_clusters[:3]):
            if fallback:
                proposals.append(
                    self._body_proposal(
                        task_id, cluster, i,
                        title=f"【免开模降级】{cluster['cluster_name']}小改方案",
                        mold=False, cost=cluster["frequency"] * 2.0, cycle=0,
                    )
                )
            else:
                proposals.append(
                    self._body_proposal(
                        task_id, cluster, i,
                        title=f"针对{cluster['cluster_name']}的材质与结构优化",
                        mold=True, cost=6000 + i * 1500, cycle=45 + i * 15,
                    )
                )

        for i, cluster in enumerate(packaging_clusters[:2]):
            old = [30, 20, 12]
            new = [26, 18, 9]
            vol_old = volumetric_weight_kg(old)
            vol_new = volumetric_weight_kg(new)
            saving = 1.35
            proposals.append(
                ProposalItem(
                    proposal_id=f"prp_{task_id}_pkg{i + 1}",
                    task_id=task_id,
                    track_type="PACKAGING_FULFILLMENT",
                    title=f"【包装降本】{cluster['cluster_name']}盒规优化与 FBA 降档",
                    description="缩小盒规降低体积重，实现 FBA 履约费降档。",
                    cost_estimation_usd=200.0 + i * 100,
                    mold_opening_required=False,
                    mold_cycle_days=0,
                    estimated_roi=2.1 + i * 0.3,
                    defect_rate_reduction=0.35 + i * 0.05,
                    status="PENDING",
                    veto_reason=None,
                    fallback_applied=fallback,
                    source_cluster_ids=[cluster["cluster_id"]],
                    evidence_review_count=cluster["frequency"],
                    evidence_image_count=len(cluster["sample_image_ids"]),
                    package_size_old_cm=old,
                    package_size_new_cm=new,
                    volumetric_weight_old_kg=vol_old,
                    volumetric_weight_new_kg=vol_new,
                    fba_tier_old=fba_tier_for(vol_old),
                    fba_tier_new=fba_tier_for(vol_new),
                    fulfillment_saving_usd_per_unit=saving,
                )
            )
        return proposals

    def _body_proposal(
        self, task_id: str, cluster: ClusterItem, index: int,
        title: str, mold: bool, cost: float, cycle: int,
    ) -> ProposalItem:
        return ProposalItem(
            proposal_id=f"prp_{task_id}_body{index + 1}",
            task_id=task_id,
            track_type="BODY_OPTIMIZATION",
            title=title,
            description=f"针对 {cluster['frequency_ratio']:.0%} 的「{cluster['cluster_name']}」差评，提出结构性改进方案。",
            cost_estimation_usd=cost,
            mold_opening_required=mold,
            mold_cycle_days=cycle,
            estimated_roi=1.8 + index * 0.4,
            defect_rate_reduction=0.55 + index * 0.05,
            status="PENDING",
            veto_reason=None,
            fallback_applied=not mold,
            source_cluster_ids=[cluster["cluster_id"]],
            evidence_review_count=cluster["frequency"],
            evidence_image_count=len(cluster["sample_image_ids"]),
        )


class DeterministicEvidenceProvider:
    async def trace(
        self,
        task_id: str,
        proposals: list[ProposalItem],
        clusters: list[ClusterItem],
        evidences: list[VisualEvidence] | None = None,
    ) -> list[EvidenceLinkItem]:
        by_id = {c["cluster_id"]: c for c in clusters}
        links: list[EvidenceLinkItem] = []
        for proposal in proposals:
            for cluster_id in proposal["source_cluster_ids"]:
                cluster = by_id.get(cluster_id)
                if cluster is None:
                    continue  # never fabricate evidence for a missing cluster
                links.append(
                    EvidenceLinkItem(
                        proposal_id=proposal["proposal_id"],
                        cluster_id=cluster_id,
                        review_ids=cluster["review_ids"],
                        image_ids=cluster["sample_image_ids"],
                    )
                )
            own = [l for l in links if l["proposal_id"] == proposal["proposal_id"]]
            review_count = sum(len(l["review_ids"]) for l in own)
            image_count = sum(len(l["image_ids"]) for l in own)
            proposal["evidence_review_count"] = review_count or proposal["evidence_review_count"]
            proposal["evidence_image_count"] = image_count or proposal["evidence_image_count"]
        return links


class DeterministicBacktestProvider:
    async def evaluate(self, task_id: str, clusters: list[ClusterItem]) -> float:
        return 0.78


class DeterministicFinancialProvider:
    """规则引擎即最终否决者；deterministic 模式不做持久化。"""

    def __init__(self, engine: FinancialEngine | None = None) -> None:
        self.engine = engine or FinancialEngine()

    def evaluate_proposal(self, proposal: dict, constraint: dict) -> Any:
        return self.engine.evaluate_proposal(proposal, constraint)

    async def record(
        self, task_id: str, proposals: list[ProposalItem],
        constraint: dict, retry_count: int,
    ) -> None:
        return None


class DeterministicProviders:
    """Bundle of all deterministic providers used by the default graph."""

    def __init__(self) -> None:
        self.engine = FinancialEngine()
        self.reviews = DeterministicReviewProvider()
        self.vision = DeterministicVisionProvider()
        self.cluster = DeterministicClusterProvider()
        self.decision = DeterministicDecisionProvider(self.engine)
        self.evidence = DeterministicEvidenceProvider()
        self.backtest = DeterministicBacktestProvider()
        self.financial = DeterministicFinancialProvider(self.engine)
