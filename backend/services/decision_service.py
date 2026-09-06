"""Dual-track decision service: clusters → BODY_OPTIMIZATION / PACKAGING_FULFILLMENT proposals.

LLM 只负责标题/描述文案；track 归属、成本与包装参数由规则计算，
输出严格为 BODY_OPTIMIZATION / PACKAGING_FULFILLMENT 两栏。
"""

import logging
from typing import Any

from agents.state import ClusterItem, ProposalItem
from runtime.event_store import utc_now_iso
from services.financial import fba_tier_for, volumetric_weight_kg

logger = logging.getLogger(__name__)

TRACK_TYPES = {"BODY_OPTIMIZATION", "PACKAGING_FULFILLMENT"}


class DecisionService:
    def __init__(self, llm=None) -> None:
        self.llm = llm

    async def decide(
        self,
        task_id: str,
        clusters: list[ClusterItem],
        constraint: dict[str, Any],
        retry_count: int,
    ) -> list[ProposalItem]:
        fallback = retry_count > 0
        body_clusters = [c for c in clusters if c["issue_type"] != "packaging_delivery"]
        packaging_clusters = [c for c in clusters if c["issue_type"] == "packaging_delivery"]

        proposals: list[ProposalItem] = []
        for i, cluster in enumerate(body_clusters[:3]):
            if fallback:
                proposals.append(
                    self._body(task_id, cluster, i, fallback=True)
                )
            else:
                proposals.append(self._body(task_id, cluster, i, fallback=False))
        for i, cluster in enumerate(packaging_clusters[:2]):
            proposals.append(self._packaging(task_id, cluster, i, fallback))

        for p in proposals:
            p["created_at"] = utc_now_iso()

        if self.llm is not None and proposals:
            await self._polish(proposals)
        return proposals

    @staticmethod
    def _body(task_id: str, cluster: ClusterItem, index: int, fallback: bool) -> ProposalItem:
        if fallback:
            return ProposalItem(
                proposal_id=f"prp_{task_id}_body{index + 1}",
                task_id=task_id,
                track_type="BODY_OPTIMIZATION",
                title=f"【免开模降级】{cluster['cluster_name']}小改方案",
                description=(
                    f"针对 {cluster['frequency_ratio']:.0%} 的「{cluster['cluster_name']}」差评，"
                    "采用替换材质/增加卡扣等免开模小改，投资压缩到毛利承受范围内。"
                ),
                cost_estimation_usd=round(cluster["frequency"] * 2.0, 2),
                mold_opening_required=False,
                mold_cycle_days=0,
                estimated_roi=1.5 + index * 0.2,
                defect_rate_reduction=0.35 + index * 0.05,
                status="PENDING",
                veto_reason=None,
                fallback_applied=True,
                source_cluster_ids=[cluster["cluster_id"]],
                evidence_review_count=cluster["frequency"],
                evidence_image_count=len(cluster["sample_image_ids"]),
            )
        return ProposalItem(
            proposal_id=f"prp_{task_id}_body{index + 1}",
            task_id=task_id,
            track_type="BODY_OPTIMIZATION",
            title=f"针对{cluster['cluster_name']}的材质与结构优化",
            description=(
                f"针对 {cluster['frequency_ratio']:.0%} 的「{cluster['cluster_name']}」差评，"
                "替换材质并优化结构公差，降低故障率。"
            ),
            cost_estimation_usd=6000 + index * 1500,
            mold_opening_required=True,
            mold_cycle_days=45 + index * 15,
            estimated_roi=1.8 + index * 0.4,
            defect_rate_reduction=0.55 + index * 0.05,
            status="PENDING",
            veto_reason=None,
            fallback_applied=False,
            source_cluster_ids=[cluster["cluster_id"]],
            evidence_review_count=cluster["frequency"],
            evidence_image_count=len(cluster["sample_image_ids"]),
        )

    @staticmethod
    def _packaging(task_id: str, cluster: ClusterItem, index: int, fallback: bool) -> ProposalItem:
        old = [30, 20, 12]
        new = [26, 18, 9]
        vol_old = volumetric_weight_kg(old)
        vol_new = volumetric_weight_kg(new)
        return ProposalItem(
            proposal_id=f"prp_{task_id}_pkg{index + 1}",
            task_id=task_id,
            track_type="PACKAGING_FULFILLMENT",
            title=f"【包装降本】{cluster['cluster_name']}盒规优化与 FBA 降档",
            description="缩小盒规降低体积重，实现 FBA 履约费降档，减少运输破损差评。",
            cost_estimation_usd=200.0 + index * 100,
            mold_opening_required=False,
            mold_cycle_days=0,
            estimated_roi=2.1 + index * 0.3,
            defect_rate_reduction=0.35 + index * 0.05,
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
            fulfillment_saving_usd_per_unit=1.35,
        )

    async def _polish(self, proposals: list[ProposalItem]) -> None:
        """LLM 仅改写标题/描述文案；结构字段保持规则计算结果。"""
        from pydantic import BaseModel

        class Polish(BaseModel):
            model_config = {"extra": "allow"}

        try:
            prompt = (
                "为以下改款提案各生成一句更具体的中文描述（title 保持，description 优化为 "
                "包含材质/结构/工艺细节的一句话）。以 JSON 数组输出："
                '[{"proposal_id": "...", "description": "..."}]。提案：'
                + "\n".join(
                    f"{p['proposal_id']}: {p['title']}（{p['track_type']}）" for p in proposals
                )
            )
            text = await self.llm.complete(prompt)
            import json

            items = json.loads(text) if isinstance(text, str) else text
            by_id = {item.get("proposal_id"): item.get("description") for item in items}
            for p in proposals:
                new_desc = by_id.get(p["proposal_id"])
                if new_desc:
                    p["description"] = new_desc
        except Exception:  # noqa: BLE001 - 文案失败不影响提案结构
            logger.warning("decision: LLM 文案润色失败，保留规则文案", exc_info=True)
