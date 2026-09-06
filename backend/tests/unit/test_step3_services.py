"""Cluster / review-filter / cache / decision / evidence / degrade tests."""

from crawler.base import UpstreamError, is_meaningless
from crawler.fake import FakeAmazonDataProvider
from core.embedding import FakeEmbeddingService
from services.cluster_service import ClusterService, severity_level
from services.decision_service import DecisionService
from services.evidence_service import EvidenceService
from services.providers import DeterministicReviewProvider, DeterministicVisionProvider
from services.review_service import ReviewService
from services.vision_service import VisionAuditService

PROPOSAL_FIELDS = {
    "proposal_id", "task_id", "track_type", "title", "description",
    "cost_estimation_usd", "mold_opening_required", "mold_cycle_days",
    "estimated_roi", "defect_rate_reduction", "status", "veto_reason",
    "fallback_applied", "source_cluster_ids", "evidence_review_count",
    "evidence_image_count",
}


async def make_reviews() -> list[dict]:
    return await DeterministicReviewProvider().fetch("B0C1234ABC", "US", 6, 40)


def test_meaningless_review_filtering():
    assert is_meaningless("ok")
    assert is_meaningless("Good")
    assert is_meaningless("Fast shipping")
    assert is_meaningless("")
    assert not is_meaningless("The handle broke after one week of normal use")


async def test_review_service_filters_and_caches():
    service = ReviewService(FakeAmazonDataProvider())
    first = await service.fetch_for_task("B0C1234ABC", "US", 6, 40, persist=False)
    second = await service.fetch_for_task("B0C1234ABC", "US", 6, 40, persist=False)
    other = await service.fetch_for_task("B0D9999XYZ", "US", 6, 40, persist=False)

    assert not first.cache_hit
    assert second.cache_hit  # 同 ASIN 缓存期内复用
    assert not other.cache_hit  # 不同 ASIN 不复用
    assert first.filtered_count > 0  # 无意义短评被过滤
    assert all(len(r["content"]) >= 12 for r in first.reviews)


async def test_cluster_service_top5_and_severity():
    service = ClusterService(FakeEmbeddingService())
    reviews = await make_reviews()
    evidences = await DeterministicVisionProvider().audit(reviews)
    clusters = await service.cluster(reviews, evidences)

    assert 1 <= len(clusters) <= 5
    for c in clusters:
        assert c["cluster_id"] and c["cluster_name"]
        assert c["issue_type"] in {
            "product_defect", "function_defect", "size_spec", "accessory",
            "manual", "packaging_delivery", "other",
        }
        assert c["severity_level"] == severity_level(c["severity_score"])
        assert c["sample_quotes"] and c["sample_quotes"][0]["review_id"] in set(c["review_ids"])


async def test_decision_service_schema():
    service = DecisionService()
    reviews = await make_reviews()
    evidences = await DeterministicVisionProvider().audit(reviews)
    clusters = await ClusterService(FakeEmbeddingService()).cluster(reviews, evidences)
    proposals = await service.decide("tsk_x", clusters, {}, retry_count=0)

    assert proposals, "clusters 应生成至少一条提案"
    for p in proposals:
        assert set(p.keys()) >= PROPOSAL_FIELDS
        assert p["track_type"] in {"BODY_OPTIMIZATION", "PACKAGING_FULFILLMENT"}
        if p["track_type"] == "PACKAGING_FULFILLMENT":
            assert {"package_size_old_cm", "package_size_new_cm", "fba_tier_old",
                    "fba_tier_new", "fulfillment_saving_usd_per_unit"} <= set(p.keys())


async def test_decision_fallback_track():
    service = DecisionService()
    reviews = await make_reviews()
    clusters = await ClusterService(FakeEmbeddingService()).cluster(reviews, [])
    proposals = await service.decide("tsk_x", clusters, {}, retry_count=1)

    for p in proposals:
        assert p["fallback_applied"]
        assert not p["mold_opening_required"]


async def test_evidence_integrity():
    reviews = await make_reviews()
    evidences = await DeterministicVisionProvider().audit(reviews)
    clusters = await ClusterService(FakeEmbeddingService()).cluster(reviews, evidences)
    proposals = await DecisionService().decide("tsk_x", clusters, {}, 0)
    links = EvidenceService().trace(proposals, clusters, evidences)

    cluster_ids = {c["cluster_id"] for c in clusters}
    review_ids = {r["review_id"] for r in reviews}
    image_ids = {e["image_id"] for e in evidences}
    assert links
    for link in links:
        assert link["cluster_id"] in cluster_ids
        assert set(link["review_ids"]) <= review_ids, "证据 review_id 必须真实存在"
        assert set(link["image_ids"]) <= image_ids, "证据 image_id 必须真实存在"


def test_evidence_never_fabricates_missing_cluster():
    service = EvidenceService()
    proposals = [{
        "proposal_id": "prp_1", "source_cluster_ids": ["clu_99"],
        "evidence_review_count": 0, "evidence_image_count": 0,
    }]
    links = service.trace(proposals, [], [])
    assert links == []
    assert proposals[0]["evidence_review_count"] == 0


async def test_vision_degrades_without_llm():
    service = VisionAuditService(llm=None)
    reviews = await make_reviews()
    evidences = await service.audit(reviews)
    assert evidences == []  # 纯文本降级，不报错


async def test_upstream_error_is_explicit():
    class ExplodingProvider:
        async def fetch(self, *args, **kwargs):
            raise UpstreamError("Amazon 数据源连续 3 次请求失败: timeout")

    service = ReviewService(ExplodingProvider())
    try:
        await service.fetch_for_task("B0C1234ABC", "US", 6, 40, persist=False)
        raise AssertionError("应抛出 UpstreamError")
    except UpstreamError as exc:
        assert "3 次" in str(exc)


async def test_fake_embedding_1024_and_normalized():
    import math

    vectors = await FakeEmbeddingService().embed(["handle broke", "color different"])
    assert len(vectors) == 2
    for v in vectors:
        assert len(v) == 1024
        assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-6
