"""Repositories for workflow results: clusters, proposals, evidence, financial."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    ClusterModel,
    EvidenceLinkModel,
    FinancialResultModel,
    ReformProposalModel,
)


class ClusterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_for_task(self, task_id: str, clusters: list[dict[str, Any]]) -> int:
        existing = (
            await self.session.scalars(
                select(ClusterModel).where(ClusterModel.task_id == task_id)
            )
        ).all()
        for row in existing:
            await self.session.delete(row)
        for cluster in clusters:
            self.session.add(
                ClusterModel(
                    task_id=task_id,
                    cluster_id=cluster["cluster_id"],
                    cluster_name=cluster["cluster_name"],
                    issue_type=cluster["issue_type"],
                    frequency=cluster.get("frequency", 0),
                    frequency_ratio=cluster.get("frequency_ratio", 0.0),
                    severity_score=cluster.get("severity_score", 0.0),
                    severity_level=cluster.get("severity_level", "minor"),
                    keywords=cluster.get("keywords", []),
                    sample_quotes=cluster.get("sample_quotes", []),
                    sample_image_ids=cluster.get("sample_image_ids", []),
                    review_ids=cluster.get("review_ids", []),
                )
            )
        await self.session.flush()
        return len(clusters)

    async def list_for_task(self, task_id: str) -> list[ClusterModel]:
        rows = (
            await self.session.scalars(
                select(ClusterModel)
                .where(ClusterModel.task_id == task_id)
                .order_by(ClusterModel.severity_score.desc())
            )
        ).all()
        return list(rows)


class ProposalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_for_task(self, task_id: str, proposals: list[dict[str, Any]]) -> int:
        existing = (
            await self.session.scalars(
                select(ReformProposalModel).where(ReformProposalModel.task_id == task_id)
            )
        ).all()
        for row in existing:
            await self.session.delete(row)
        for p in proposals:
            packaging_keys = (
                "package_size_old_cm", "package_size_new_cm",
                "volumetric_weight_old_kg", "volumetric_weight_new_kg",
                "fba_tier_old", "fba_tier_new", "fulfillment_saving_usd_per_unit",
            )
            packaging_meta = {k: p[k] for k in packaging_keys if k in p} or None
            self.session.add(
                ReformProposalModel(
                    proposal_id=p["proposal_id"],
                    task_id=task_id,
                    track_type=p["track_type"],
                    title=p["title"],
                    description=p["description"],
                    cost_estimation_usd=p.get("cost_estimation_usd"),
                    mold_opening_required=p.get("mold_opening_required", False),
                    mold_cycle_days=p.get("mold_cycle_days", 0),
                    estimated_roi=p.get("estimated_roi"),
                    defect_rate_reduction=p.get("defect_rate_reduction"),
                    status=p.get("status", "PENDING"),
                    veto_reason=p.get("veto_reason"),
                    fallback_applied=p.get("fallback_applied", False),
                    source_cluster_ids=p.get("source_cluster_ids", []),
                    evidence_review_ids=p.get("evidence_review_ids", []),
                    evidence_image_ids=p.get("evidence_image_ids", []),
                    packaging_meta=packaging_meta,
                )
            )
        await self.session.flush()
        return len(proposals)

    async def get(self, proposal_id: str) -> ReformProposalModel | None:
        return await self.session.scalar(
            select(ReformProposalModel).where(ReformProposalModel.proposal_id == proposal_id)
        )

    async def list_for_task(self, task_id: str) -> list[ReformProposalModel]:
        rows = (
            await self.session.scalars(
                select(ReformProposalModel).where(ReformProposalModel.task_id == task_id)
            )
        ).all()
        return list(rows)

    async def count_vetoed(self, days: int = 30) -> int:
        return int(
            await self.session.scalar(
                select(func.count()).select_from(ReformProposalModel).where(
                    ReformProposalModel.status == "VETOED"
                )
            )
            or 0
        )


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_for_proposals(self, links: list[dict[str, Any]]) -> int:
        for link in links:
            existing = await self.session.scalar(
                select(EvidenceLinkModel).where(
                    EvidenceLinkModel.proposal_id == link["proposal_id"],
                    EvidenceLinkModel.cluster_id == link["cluster_id"],
                )
            )
            values = dict(review_ids=link.get("review_ids", []), image_ids=link.get("image_ids", []))
            if existing is not None:
                for key, value in values.items():
                    setattr(existing, key, value)
            else:
                self.session.add(
                    EvidenceLinkModel(
                        proposal_id=link["proposal_id"],
                        cluster_id=link["cluster_id"],
                        **values,
                    )
                )
        await self.session.flush()
        return len(links)

    async def list_for_proposal(self, proposal_id: str) -> list[EvidenceLinkModel]:
        rows = (
            await self.session.scalars(
                select(EvidenceLinkModel).where(EvidenceLinkModel.proposal_id == proposal_id)
            )
        ).all()
        return list(rows)


class FinancialResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, result: dict[str, Any]) -> None:
        task_id = result["task_id"]
        existing = await self.session.scalar(
            select(FinancialResultModel).where(FinancialResultModel.task_id == task_id)
        )
        values = dict(
            veto_status=result.get("veto_status", "PENDING"),
            checked_proposals=result.get("checked_proposals", 0),
            vetoed_proposal_ids=result.get("vetoed_proposal_ids", []),
            veto_reasons=result.get("veto_reasons", []),
            fallback_applied=result.get("fallback_applied", False),
            retry_count=result.get("retry_count", 0),
            financial_constraint=result.get("financial_constraint", {}),
        )
        if existing is not None:
            for key, value in values.items():
                setattr(existing, key, value)
        else:
            self.session.add(FinancialResultModel(task_id=task_id, **values))
        await self.session.flush()

    async def get(self, task_id: str) -> FinancialResultModel | None:
        return await self.session.scalar(
            select(FinancialResultModel).where(FinancialResultModel.task_id == task_id)
        )
