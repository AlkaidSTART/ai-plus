"""Unit and integration tests for ASIN extraction, keyword search, review deduplication, and analysis."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

from insightx.schemas import (
    DataQuality,
    TaskCreateRequest,
    TaskWindow,
)
from insightx.services.analysis import (
    analyze_reviews,
    deduplicate_reviews,
)
from insightx.services.asin import (
    extract_asin,
    extract_asins,
    normalize_asin_list,
)
from insightx.services.search import (
    extract_products_from_html,
    normalize_search_keyword,
    search_amazon_products_sync,
)


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    del type_, compiler, kw
    return "JSON"


@compiles(BigInteger, "sqlite")
def compile_bigint_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    del type_, compiler, kw
    return "INTEGER"


USER_EXAMPLE_URL = (
    "https://www.amazon.com/Project-Cloud-Mens-Shoes-Lightweight/dp/B0FFW9LG7S/"
    "ref=trend_26_fall_ntos_grid?pf_rd_p=ec890b45-d55a-49b8-85e2-fa63c8255d5e&"
    "pf_rd_r=C9KT38048G6JX1QFHRT7&sr=1-2-a3f25ed3-e18f-4f84-9636-46feea37aaed&th=1&psc=1"
)


class TestAsinExtraction:
    def test_extract_user_example_url(self) -> None:
        asin = extract_asin(USER_EXAMPLE_URL)
        assert asin == "B0FFW9LG7S"

    def test_extract_various_url_formats(self) -> None:
        assert extract_asin("https://www.amazon.com/dp/B0D5N57SHS") == "B0D5N57SHS"
        assert (
            extract_asin("https://www.amazon.com/gp/product/B0052TBWM4") == "B0052TBWM4"
        )
        assert (
            extract_asin("https://www.amazon.com/product/B09YBLCL41?th=1")
            == "B09YBLCL41"
        )
        assert (
            extract_asin("https://www.amazon.com/gp/aw/d/B0BS6G9WG6/") == "B0BS6G9WG6"
        )
        assert extract_asin("https://a.co/d/B0D22VJ984") == "B0D22VJ984"
        assert (
            extract_asin("https://www.amazon.com/item?asin=B0CL4XJCJW") == "B0CL4XJCJW"
        )
        assert extract_asin("B0FFW9LG7S") == "B0FFW9LG7S"
        assert extract_asin("b0ffw9lg7s") == "B0FFW9LG7S"

    def test_extract_asins_from_mixed_text(self) -> None:
        text = f"""
        Here is the first item: {USER_EXAMPLE_URL}
        And another one: https://www.amazon.com/dp/B0D5N57SHS
        And raw asin: b0052tbwm4
        Duplicate: B0FFW9LG7S
        """
        asins = extract_asins(text)
        assert asins == ["B0FFW9LG7S", "B0D5N57SHS", "B0052TBWM4"]

    def test_normalize_asin_list(self) -> None:
        inputs = [USER_EXAMPLE_URL, "B0D5N57SHS", "b0d5n57shs", "invalid_random_string"]
        normalized = normalize_asin_list(inputs)
        assert normalized == ["B0FFW9LG7S", "B0D5N57SHS"]

    def test_task_create_request_accepts_urls(self) -> None:
        req = TaskCreateRequest(
            asins=[USER_EXAMPLE_URL, "https://www.amazon.com/dp/B0D5N57SHS"],
            platform="amazon",
            marketplace="US",
            window=TaskWindow(preset="6m"),
        )
        assert req.asins == ["B0FFW9LG7S", "B0D5N57SHS"]

    def test_task_create_request_accepts_keyword(self) -> None:
        req = TaskCreateRequest(
            keyword="女性鞋子",
            platform="amazon",
            marketplace="US",
            window=TaskWindow(preset="6m"),
        )
        assert req.keyword == "女性鞋子"
        assert req.asins == []


class TestSearchAndMatching:
    def test_normalize_keyword(self) -> None:
        assert normalize_search_keyword("女性鞋子") == "women shoes"
        assert normalize_search_keyword("女鞋") == "women shoes"
        assert normalize_search_keyword("running shoes") == "running shoes"

    def test_search_catalog_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_fail(*args: object, **kwargs: object) -> object:
            raise RuntimeError("Live fetch disabled in unit test")

        monkeypatch.setattr("insightx.services.search.fetch_dom", mock_fail)
        products = search_amazon_products_sync("女性鞋子", limit=10)
        assert len(products) <= 10
        assert len(products) > 0
        asins = [p["asin"] for p in products]
        assert len(asins) == len(set(asins)), "Products must be deduplicated"

    def test_extract_products_from_html(self) -> None:
        html = """
        <div data-asin="B0FFW9LG7S">
            <h2><a href="/dp/B0FFW9LG7S"><span>Project Cloud Mens Shoes</span></a></h2>
            <span class="a-icon-alt">4.3 out of 5 stars</span>
        </div>
        <div data-asin="B0FFW9LG7S">
            <!-- duplicate asin -->
        </div>
        <div data-asin="B0D5N57SHS">
            <h2><span>Womens Fashion Sneakers</span></h2>
            <span class="a-icon-alt">4.5 out of 5 stars</span>
        </div>
        """
        products = extract_products_from_html(html, limit=10)
        assert len(products) == 2
        assert products[0]["asin"] == "B0FFW9LG7S"
        assert products[0]["title"] == "Project Cloud Mens Shoes"
        assert products[0]["rating"] == 4.3
        assert products[1]["asin"] == "B0D5N57SHS"


class TestReviewDeduplicationAndAnalysis:
    def test_deduplicate_reviews(self) -> None:
        reviews = [
            {
                "source_ref": "rev_1",
                "excerpt": "Good shoe but too narrow at the toes.",
                "rating": 3,
            },
            {
                "source_ref": "rev_1",
                "excerpt": "Good shoe but too narrow at the toes.",
                "rating": 3,
            },  # duplicate source_ref
            {
                "source_ref": "rev_2",
                "excerpt": "Good shoe but too narrow at the toes.",
                "rating": 3,
            },  # duplicate content hash
            {
                "source_ref": "rev_3",
                "excerpt": "Sole came off after one week. Terrible glue.",
                "rating": 1,
            },
        ]
        unique, excluded = deduplicate_reviews(reviews, limit=10)
        assert len(unique) == 2
        assert excluded == 2
        assert unique[0]["source_ref"] == "rev_1"
        assert unique[1]["source_ref"] == "rev_3"

    def test_review_upper_limit(self) -> None:
        reviews = [
            {
                "source_ref": f"rev_{i}",
                "excerpt": f"Review number {i} with distinct content.",
                "rating": 4,
            }
            for i in range(25)
        ]
        unique, excluded = deduplicate_reviews(reviews, limit=10)
        assert len(unique) == 10
        assert excluded == 15

    def test_analysis_generates_pain_points_and_proposals(self) -> None:
        sample_reviews = [
            {
                "source_ref": "rev_1",
                "title": "Too narrow",
                "excerpt": "These shoes are way too small and tight. Squeezed my toes and hurt my feet.",
                "rating": 2,
            },
            {
                "source_ref": "rev_2",
                "title": "Hard insole",
                "excerpt": "Sole is rock hard with zero arch support. My feet were aching after 2 hours.",
                "rating": 1,
            },
            {
                "source_ref": "rev_3",
                "title": "Terrible blister",
                "excerpt": "The heel rubbed raw blisters on my Achilles. Couldn't walk.",
                "rating": 1,
            },
            {
                "source_ref": "rev_4",
                "title": "Sole broke",
                "excerpt": "Glue fell apart and sole detached after 3 days. Cheap quality.",
                "rating": 1,
            },
            {
                "source_ref": "rev_5",
                "title": "Damaged box and chemical smell",
                "excerpt": "Packaging was crushed on arrival and had a strong chemical odor.",
                "rating": 2,
            },
        ]
        evidence_ids = [f"evd_{i}" for i in range(len(sample_reviews))]
        pain_points, proposals, quality, metrics = analyze_reviews(
            sample_reviews,
            evidence_ids=evidence_ids,
            window_preset="6m",
            excluded_count=0,
        )

        assert quality == DataQuality.SUFFICIENT
        assert len(pain_points) >= 3
        assert len(proposals) >= 4
        assert metrics["valid_review_count"] == 5
        assert metrics["raw_review_count"] == 5

        # Check dual-column proposals
        prod_props = [p for p in proposals if p.column == "PRODUCT_OPTIMIZATION"]
        pack_props = [
            p for p in proposals if p.column == "PACKAGING_FULFILLMENT_OPTIMIZATION"
        ]
        assert len(prod_props) > 0
        assert len(pack_props) > 0

        # Check evidence linking
        for p in pain_points:
            assert len(p.evidence_refs) > 0
            assert p.severity_score in {1, 2, 3, 4, 5}
            assert p.severity_level in {"CRITICAL", "MODERATE", "MINOR"}

        for prop in proposals:
            assert len(prop.pain_point_ids) > 0
            assert len(prop.evidence_refs) > 0


class TestEndpointsAndPipeline:
    def test_extract_asins_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        from insightx.main import app

        client = TestClient(app)
        res = client.post(
            "/api/v1/tasks/extract-asins",
            json={"text": f"Check this: {USER_EXAMPLE_URL} and B0D5N57SHS"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["asins"] == ["B0FFW9LG7S", "B0D5N57SHS"]

    def test_search_products_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from insightx.main import app

        async def mock_fail(*args: object, **kwargs: object) -> object:
            raise RuntimeError("Live fetch disabled in test")

        monkeypatch.setattr("insightx.services.search.fetch_dom", mock_fail)
        client = TestClient(app)
        res = client.post(
            "/api/v1/tasks/search-products",
            json={"keyword": "女性鞋子", "limit": 10},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["keyword"] == "女性鞋子"
        assert len(data["products"]) <= 10
        assert len(data["products"]) > 0
        assert data["products"][0]["asin"]

    def test_create_task_with_url_and_worker_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from sqlalchemy import BigInteger, create_engine
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy.ext.compiler import compiles
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        @compiles(JSONB, "sqlite")
        def compile_jsonb_sqlite(type_: object, compiler: object, **kw: object) -> str:
            return "JSON"

        @compiles(BigInteger, "sqlite")
        def compile_bigint_sqlite(type_: object, compiler: object, **kw: object) -> str:
            return "INTEGER"

        from insightx.crawler.fetch import FetchedPage
        from insightx.models import (
            Base,
            Evidence,
            EvidenceClaimRef,
            Report,
            Task,
            TaskItem,
        )
        from insightx.services.tasks import create_task
        from insightx.services.worker import execute_task_pipeline

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        sample_dom = {
            "type": "element",
            "tag": "html",
            "attributes": {},
            "children": [
                {
                    "type": "element",
                    "tag": "div",
                    "attributes": {"data-hook": "review", "id": "customer_review-1"},
                    "children": [
                        {
                            "type": "element",
                            "tag": "span",
                            "attributes": {"data-hook": "review-title"},
                            "children": [
                                {"type": "text", "text": "Too small and narrow"}
                            ],
                        },
                        {
                            "type": "element",
                            "tag": "span",
                            "attributes": {"data-hook": "review-body"},
                            "children": [
                                {
                                    "type": "text",
                                    "text": "These shoes are way too small and tight for my feet. Toe box is pinched.",
                                }
                            ],
                        },
                        {
                            "type": "element",
                            "tag": "i",
                            "attributes": {"data-hook": "review-star-rating"},
                            "children": [
                                {
                                    "type": "element",
                                    "tag": "span",
                                    "attributes": {},
                                    "children": [
                                        {"type": "text", "text": "2.0 out of 5 stars"}
                                    ],
                                }
                            ],
                        },
                    ],
                },
                {
                    "type": "element",
                    "tag": "div",
                    "attributes": {"data-hook": "review", "id": "customer_review-2"},
                    "children": [
                        {
                            "type": "element",
                            "tag": "span",
                            "attributes": {"data-hook": "review-title"},
                            "children": [
                                {"type": "text", "text": "Sole broke and peeled off"}
                            ],
                        },
                        {
                            "type": "element",
                            "tag": "span",
                            "attributes": {"data-hook": "review-body"},
                            "children": [
                                {
                                    "type": "text",
                                    "text": "The glue fell apart and the sole detached after one week of wear.",
                                }
                            ],
                        },
                        {
                            "type": "element",
                            "tag": "i",
                            "attributes": {"data-hook": "review-star-rating"},
                            "children": [
                                {
                                    "type": "element",
                                    "tag": "span",
                                    "attributes": {},
                                    "children": [
                                        {"type": "text", "text": "1.0 out of 5 stars"}
                                    ],
                                }
                            ],
                        },
                    ],
                },
            ],
        }

        from datetime import UTC, datetime

        async def mock_fetch(url: str, **kwargs: object) -> FetchedPage:
            return FetchedPage(
                source_url=url,
                final_url="https://www.amazon.com/dp/B0FFW9LG7S",
                http_status=200,
                title="Project Cloud Mens Shoes",
                captured_at=datetime.now(UTC),
                dom=sample_dom,
            )

        with session_factory() as session:
            req = TaskCreateRequest(
                asins=[USER_EXAMPLE_URL],
                platform="amazon",
                marketplace="US",
                window=TaskWindow(preset="6m"),
            )
            res = create_task(
                session,
                tenant_id="test_tenant",
                request=req,
                idempotency_key="idemp_1",
            )
            task_id = res.task_id
            assert res.items[0].asin == "B0FFW9LG7S"

        # Run worker pipeline
        execute_task_pipeline(session_factory, task_id, fetcher=mock_fetch)

        with session_factory() as session:
            task = session.get(Task, task_id)
            assert task.status == "COMPLETED"
            item = session.query(TaskItem).filter_by(task_id=task_id).first()
            assert item.status == "COMPLETED"

            # Check report
            report = session.query(Report).filter_by(task_id=task_id).first()
            assert report is not None
            assert len(report.pain_points) >= 2
            assert len(report.proposals) >= 4
            assert report.data_quality in {"SUFFICIENT", "PARTIAL"}

            # Check evidence and claim refs
            evidence_list = session.query(Evidence).filter_by(task_id=task_id).all()
            assert len(evidence_list) == 2

            claim_refs = session.query(EvidenceClaimRef).all()
            assert len(claim_refs) > 0
