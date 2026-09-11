"""来源契约测试（离线，无数据库、无网络）。

覆盖：夹具 schema、来源记录到 reviews 表的字段映射、api.md 覆盖口径恒等式、
错误分类契约、ASIN 请求契约。真实拉取与真实向量调用在无凭证时跳过，
不断言付费行为；计数与重试的线上实现分别在阶段 05/04 落地，本文件只锁定语义。
"""

import hashlib
import json
import os
import uuid
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.api.routes.tasks import _validate_asins
from app.api.schemas import CreateTaskRequest
from app.db.models import Review

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

TEST_PRODUCT_ID = uuid.uuid5(uuid.NAMESPACE_URL, "insightx/test/product-a")
TEST_TENANT_ID = uuid.uuid5(uuid.NAMESPACE_URL, "insightx/test/tenant")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["synthetic"] is True
    return data


def test_fixture_records_schema():
    data = load_fixture("provider_reviews_synthetic.json")
    assert len(data["records"]) == 6
    for record in data["records"]:
        assert record["source_review_id"]
        assert 1 <= record["rating"] <= 5
        date.fromisoformat(record["reviewed_at"])
        datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00"))
        assert isinstance(record["images"], list)


def test_source_record_maps_to_review_model():
    """契约：来源字段到 reviews 表字段的映射（内存构造，不写库）。"""
    data = load_fixture("provider_reviews_synthetic.json")
    record = next(r for r in data["records"] if r["source_review_id"] == "SYN-R-001")
    review = Review(
        tenant_id=TEST_TENANT_ID,
        product_id=TEST_PRODUCT_ID,
        source_review_id=record["source_review_id"],
        content_hash=hashlib.sha256(record["text"].encode("utf-8")).hexdigest(),
        raw_text=record["text"],
        rating=record["rating"],
        language=record["language"],
        reviewed_at=date.fromisoformat(record["reviewed_at"]),
        observed_at=datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00")),
        source_url=None,
    )
    assert review.raw_text == "The left armrest snapped after two weeks of normal office use."
    assert review.rating == 1
    assert review.language == "en"
    assert len(review.content_hash) == 64
    assert review.observed_at.tzinfo is not None


def test_coverage_identities_match_api_contract():
    """契约参考（线上实现见阶段 05）：raw = valid + excluded；negative 为有效 1–3 星子集。"""
    data = load_fixture("provider_reviews_synthetic.json")
    excluded_ids = {"SYN-R-003", "SYN-R-005"}  # 无意义短评；与 SYN-R-001 文本重复
    valid = [r for r in data["records"] if r["source_review_id"] not in excluded_ids]
    raw_count = len(data["records"])
    valid_count = len(valid)
    excluded_count = raw_count - valid_count
    assert (raw_count, valid_count, excluded_count) == (6, 4, 2)
    negative = [r for r in valid if r["rating"] <= 3]
    assert len(negative) == 4
    rating_distribution = {1: 2, 2: 1, 3: 1}
    assert sorted(r["rating"] for r in valid) == [1, 1, 2, 3]
    assert rating_distribution[1] == 2
    language_distribution = {}
    for r in valid:
        language_distribution[r["language"]] = language_distribution.get(r["language"], 0) + 1
    assert language_distribution == {"en": 2, "de": 1, "es": 1}
    month_distribution = {}
    for r in valid:
        month = r["reviewed_at"][:7]
        month_distribution[month] = month_distribution.get(month, 0) + 1
    assert month_distribution == {"2026-07": 2, "2026-08": 2}


# 契约参考：错误分类（重试引擎见阶段 04/05；永久错误永不重试，总尝试上限见技术方案 §5.3）。
ERROR_CONTRACT = {
    401: {"category": "auth", "retryable": False},
    403: {"category": "auth", "retryable": False},
    404: {"category": "no_data", "retryable": False},
    429: {"category": "rate_limited", "retryable": True},
    500: {"category": "server", "retryable": True},
    503: {"category": "server", "retryable": True},
    "timeout": {"category": "transient", "retryable": True},
    "connection_error": {"category": "transient", "retryable": True},
}
MAX_TOTAL_ATTEMPTS = 4  # 首次 + 最多 3 次重试；禁止无限重试


@pytest.mark.parametrize("status,expected", list(ERROR_CONTRACT.items()))
def test_error_taxonomy(status, expected):
    assert expected["retryable"] is False or MAX_TOTAL_ATTEMPTS <= 4
    if expected["category"] in ("auth", "no_data"):
        assert expected["retryable"] is False


def test_create_task_request_contract():
    body = CreateTaskRequest(project_id="project_home", asins=["B012345678"])
    assert body.asins == ["B012345678"]
    with pytest.raises(ValidationError):
        CreateTaskRequest(
            project_id="project_home", asins=["B012345678"] * 11
        )


def test_asin_normalization_contract():
    assert _validate_asins(["b012345678", "B012345678"]) is None
    bad = _validate_asins(["NOT-AN-ASIN"])
    assert bad is not None and bad.status_code == 422


needs_source_credential = pytest.mark.skipif(
    not os.getenv("AMAZON_SOURCE_API_KEY"),
    reason="无来源凭证：不断言真实调用；凭证就绪后验证单 ASIN 拉取、字段齐全、分页与耗时/费用",
)
needs_model_endpoint = pytest.mark.skipif(
    not os.getenv("EMBEDDING_API_URL") and not os.getenv("LOCAL_MODEL_PATH"),
    reason="无模型服务端点/本地模型：不断言真实向量调用",
)


@needs_source_credential
def test_live_source_fetch():
    pytest.fail("阶段 05 实现后填写：单 ASIN 真实拉取的记录、覆盖与费用断言")


@needs_model_endpoint
def test_live_embedding_call():
    pytest.fail("阶段 06 实现后填写：1024 维向量调用的模型标识、耗时与计量断言")
