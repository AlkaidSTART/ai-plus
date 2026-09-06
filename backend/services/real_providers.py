"""Real provider bundle: replaces the deterministic providers behind the same
interfaces (Step 3). The graph and nodes are untouched.

- Reviews: AmazonDataProvider (configurable gateway; Fake when unconfigured)
  → cleaning → PostgreSQL persistence, with a 24h reuse cache.
- Clustering: embeddings + similarity (bge-m3 when installed, deterministic
  fallback otherwise), rule-based severity, optional LLM labeling.
- Vision: Claude Vision when a key is configured; graceful text-only degrade.
- Decision: rule-computed structure + optional LLM copywriting.
- Financial: deterministic rule engine + PostgreSQL persistence.
"""

import logging
from typing import Any

from core.config import Settings
from core.embedding import build_embedding_from_settings
from core.llm import build_llm_from_settings
from crawler.fake import FakeAmazonDataProvider
from crawler.http_provider import ConfigurableHttpAmazonProvider
from services.cluster_service import ClusterService
from services.decision_service import DecisionService
from services.evidence_service import EvidenceService
from services.financial import FinancialEngine
from services.review_service import ReviewService
from services.vision_service import VisionAuditService

logger = logging.getLogger(__name__)


def _persist_best_effort(coro_label: str, coro_factory) -> None:
    """Fire-and-forget DB persistence; failures are logged, never fatal."""

    async def _runner():
        try:
            await coro_factory()
        except Exception:  # noqa: BLE001
            logger.exception("persistence failed: %s", coro_label)

    import asyncio

    try:
        asyncio.get_running_loop().create_task(_runner())
    except RuntimeError:
        logger.warning("persistence skipped (no running loop): %s", coro_label)


class RealProviders:
    def __init__(self, settings: Settings) -> None:
        self.engine = FinancialEngine()
        self.llm = build_llm_from_settings(settings)
        self.embedding = build_embedding_from_settings(settings)

        if settings.AMAZON_API_BASE_URL:
            amazon: Any = ConfigurableHttpAmazonProvider(
                base_url=settings.AMAZON_API_BASE_URL,
                api_key=settings.AMAZON_API_KEY,
            )
        else:
            logger.warning("AMAZON_API_BASE_URL 未配置，使用 FakeAmazonDataProvider（演示数据）")
            amazon = FakeAmazonDataProvider()
        self.review_service = ReviewService(
            amazon, cache_ttl_hours=settings.REVIEW_CACHE_TTL_HOURS
        )
        self.cluster_service = ClusterService(self.embedding, self.llm)
        self.vision_service = VisionAuditService(self.llm)
        self.decision_service = DecisionService(self.llm)
        self.evidence_service = EvidenceService()

        # ---- provider protocol adapters (same shapes as DeterministicProviders) ----
        outer = self

        class ReviewProviderImpl:
            async def fetch(self, asin, marketplace, window_months, max_reviews):
                outcome = await outer.review_service.fetch_for_task(
                    asin, marketplace, window_months, max_reviews
                )
                return outcome.reviews

        class VisionProviderImpl:
            async def audit(self, reviews):
                return await outer.vision_service.audit(reviews)

        class ClusterProviderImpl:
            async def cluster(self, task_id, reviews, evidences):
                clusters = await outer.cluster_service.cluster(reviews, evidences)
                if clusters:
                    _persist_best_effort(
                        f"clusters:{task_id}",
                        lambda: outer._persist_clusters(task_id, clusters),
                    )
                return clusters

        class DecisionProviderImpl:
            async def decide(self, task_id, clusters, constraint, retry_count):
                proposals = await outer.decision_service.decide(
                    task_id, clusters, constraint, retry_count
                )
                _persist_best_effort(
                    f"proposals:{task_id}",
                    lambda: outer._persist_proposals(task_id, proposals),
                )
                return proposals

        class EvidenceProviderImpl:
            async def trace(self, task_id, proposals, clusters, evidences=None):
                links = outer.evidence_service.trace(proposals, clusters, evidences or [])
                _persist_best_effort(
                    f"evidence:{task_id}", lambda: outer._persist_evidence(links)
                )
                return links

        class BacktestProviderImpl:
            async def evaluate(self, task_id, clusters):
                # 正式回测属 P2；当前返回确定性占位分数，enable_backtest 默认关闭
                return 0.78

        class FinancialProviderImpl:
            engine = outer.engine

            def evaluate_proposal(self, proposal, constraint):
                return outer.engine.evaluate_proposal(proposal, constraint)

            async def record(self, task_id, proposals, constraint, retry_count):
                _persist_best_effort(
                    f"financial:{task_id}", lambda: outer._persist_financial(
                        task_id, proposals, constraint, retry_count
                    )
                )

        self.reviews = ReviewProviderImpl()
        self.vision = VisionProviderImpl()
        self.cluster = ClusterProviderImpl()
        self.decision = DecisionProviderImpl()
        self.evidence = EvidenceProviderImpl()
        self.backtest = BacktestProviderImpl()
        self.financial = FinancialProviderImpl()

    async def _persist_clusters(self, task_id: str, clusters) -> None:
        from db.repositories.result_repositories import ClusterRepository
        from db.session import get_sessionmaker

        async with get_sessionmaker()() as session:
            await ClusterRepository(session).replace_for_task(
                task_id, [dict(c) for c in clusters]
            )
            await session.commit()

    async def _persist_proposals(self, task_id: str, proposals) -> None:
        from db.repositories.result_repositories import ProposalRepository
        from db.session import get_sessionmaker

        async with get_sessionmaker()() as session:
            await ProposalRepository(session).replace_for_task(
                task_id, [dict(p) for p in proposals]
            )
            await session.commit()

    async def _persist_evidence(self, links) -> None:
        from db.repositories.result_repositories import EvidenceRepository
        from db.session import get_sessionmaker

        async with get_sessionmaker()() as session:
            await EvidenceRepository(session).replace_for_proposals(
                [dict(l) for l in links]
            )
            await session.commit()

    async def _persist_financial(
        self, task_id: str, proposals, constraint, retry_count
    ) -> None:
        from db.repositories.result_repositories import FinancialResultRepository
        from db.session import get_sessionmaker

        vetoed = [p["proposal_id"] for p in proposals if p.get("status") == "VETOED"]
        reasons = [p.get("veto_reason") for p in proposals if p.get("veto_reason")]
        async with get_sessionmaker()() as session:
            await FinancialResultRepository(session).upsert(
                {
                    "task_id": task_id,
                    "veto_status": "VETOED" if vetoed else "PASSED",
                    "checked_proposals": len(proposals),
                    "vetoed_proposal_ids": vetoed,
                    "veto_reasons": reasons,
                    "fallback_applied": retry_count > 0,
                    "retry_count": retry_count,
                    "financial_constraint": constraint,
                }
            )
            await session.commit()
