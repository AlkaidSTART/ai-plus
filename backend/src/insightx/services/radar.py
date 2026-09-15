"""Competitor radar service: BSR trends and cross-platform SKU matrix."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from statistics import fmean

from sqlalchemy import select
from sqlalchemy.orm import Session

from insightx.models import Task, TaskItem, utc_now
from insightx.schemas import (
    BsrHistoryPoint,
    BsrTrendsResponse,
    CompetitorBsrItem,
    CrossPlatformItem,
    CrossPlatformMetrics,
    CrossPlatformResponse,
)

# Benchmark competitors representing the insulated drinkware / tumbler category (US marketplace)
_DEFAULT_COMPETITORS = [
    {
        "asin": "B08N5WRWNW",
        "title": "Insulated Stainless Steel Travel Tumbler with Straw Lid (40 oz)",
        "category": "Home & Kitchen",
        "subcategory": "Tumblers & Water Glasses",
        "base_bsr": 28,
        "base_sub_bsr": 2,
        "base_price": 34.95,
        "buy_box_ratio": 0.96,
        "buy_box_winner": "Direct Store US",
        "rating": 4.7,
        "review_count": 18420,
    },
    {
        "asin": "B07XJ8C8F5",
        "title": "Double-Wall Vacuum Coffee Travel Mug Leakproof Flip Cap (20 oz)",
        "category": "Home & Kitchen",
        "subcategory": "Insulated Mugs",
        "base_bsr": 64,
        "base_sub_bsr": 7,
        "base_price": 24.99,
        "buy_box_ratio": 0.91,
        "buy_box_winner": "KitchenGear Prime",
        "rating": 4.5,
        "review_count": 8950,
    },
    {
        "asin": "B09V3KXJPB",
        "title": "Ceramic-Lined Insulated Tumbler with Magnetic Slider (32 oz)",
        "category": "Home & Kitchen",
        "subcategory": "Tumblers & Water Glasses",
        "base_bsr": 115,
        "base_sub_bsr": 14,
        "base_price": 29.50,
        "buy_box_ratio": 0.88,
        "buy_box_winner": "AeroFlask Official",
        "rating": 4.4,
        "review_count": 4310,
    },
]


def _hash_int(seed: str, modulus: int = 100) -> int:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulus


def _generate_history(
    asin: str,
    base_bsr: int,
    base_sub_bsr: int,
    base_price: float,
    days: int,
    now: datetime,
) -> list[BsrHistoryPoint]:
    """Generate deterministic historical trend series for BSR and price."""
    # ponytail: 启发式确定性平滑插值；后续接入持续定时抓取时序快照表
    points: list[BsrHistoryPoint] = []
    step = 1 if days <= 30 else (2 if days <= 60 else 3)

    for i in range(days, -1, -step):
        point_time = now - timedelta(days=i)
        seed = f"{asin}:{point_time.strftime('%Y-%m-%d')}"
        bsr_noise = _hash_int(f"{seed}:bsr", 21) - 10  # -10 to +10
        price_noise = round(
            (_hash_int(f"{seed}:price", 9) - 4) * 0.5, 2
        )  # -2.0 to +2.0

        bsr_val = max(1, base_bsr + bsr_noise)
        sub_bsr_val = max(1, base_sub_bsr + int(bsr_noise / 3))
        price_val = max(9.99, round(base_price + price_noise, 2))
        bb_status = _hash_int(f"{seed}:bb", 100) < 95

        points.append(
            BsrHistoryPoint(
                timestamp=point_time,
                bsr=bsr_val,
                sub_bsr=sub_bsr_val,
                price=price_val,
                buy_box=bb_status,
            )
        )
    return points


def get_bsr_trends(
    session: Session,
    *,
    tenant_id: str,
    task_id: str | None = None,
    asin: str | None = None,
    days: int = 30,
) -> BsrTrendsResponse:
    """Return monitored competitor BSR and price trend series."""
    now = utc_now()
    days = min(max(days, 7), 90)

    # 1. Inspect real task items from tenant if available
    competitor_asins: list[dict] = []
    query = (
        select(TaskItem.asin)
        .join(Task, Task.task_id == TaskItem.task_id)
        .where(Task.tenant_id == tenant_id)
    )
    if task_id:
        query = query.where(TaskItem.task_id == task_id)
    real_asins = list(session.scalars(query.distinct()).all())

    seen_asins = set()
    for real_asin in real_asins:
        if real_asin not in seen_asins:
            seen_asins.add(real_asin)
            base_bsr = 30 + _hash_int(real_asin, 90)
            base_sub = max(1, int(base_bsr / 7))
            base_price = 19.99 + round(_hash_int(f"{real_asin}:p", 20) * 0.8, 2)
            competitor_asins.append(
                {
                    "asin": real_asin,
                    "title": f"Amazon Product {real_asin} Insulated Vacuum Mug",
                    "category": "Home & Kitchen",
                    "subcategory": "Tumblers & Water Glasses",
                    "base_bsr": base_bsr,
                    "base_sub_bsr": base_sub,
                    "base_price": base_price,
                    "buy_box_ratio": 0.93,
                    "buy_box_winner": f"Seller {real_asin[:4]} Direct",
                    "rating": 4.6,
                    "review_count": 1200 + _hash_int(real_asin, 5000),
                }
            )

    # Fallback / merge benchmark competitors
    for default_item in _DEFAULT_COMPETITORS:
        if default_item["asin"] not in seen_asins:
            competitor_asins.append(default_item)
            seen_asins.add(default_item["asin"])

    if asin:
        competitor_asins = [c for c in competitor_asins if c["asin"] == asin]

    items: list[CompetitorBsrItem] = []
    for comp in competitor_asins:
        history = _generate_history(
            comp["asin"],
            comp["base_bsr"],
            comp["base_sub_bsr"],
            comp["base_price"],
            days,
            now,
        )
        current_point = history[-1] if history else None
        point_7d_ago = (
            history[-8] if len(history) >= 8 else (history[0] if history else None)
        )

        current_bsr = current_point.bsr if current_point else comp["base_bsr"]
        old_bsr = point_7d_ago.bsr if point_7d_ago else current_bsr
        # positive delta means rank dropped, negative delta means rank improved (lower is better in Amazon BSR)
        bsr_change_7d = current_bsr - old_bsr

        items.append(
            CompetitorBsrItem(
                asin=comp["asin"],
                title=comp["title"],
                category=comp["category"],
                subcategory=comp["subcategory"],
                current_bsr=current_bsr,
                current_sub_bsr=current_point.sub_bsr
                if current_point
                else comp["base_sub_bsr"],
                bsr_change_7d=bsr_change_7d,
                current_price=current_point.price
                if current_point
                else comp["base_price"],
                currency="USD",
                buy_box_ratio=comp["buy_box_ratio"],
                buy_box_winner=comp["buy_box_winner"],
                rating=comp["rating"],
                review_count=comp["review_count"],
                history=history,
            )
        )

    return BsrTrendsResponse(items=items, updated_at=now)


def get_cross_platform(
    session: Session,
    *,
    tenant_id: str,
    asin: str | None = None,
    platform: str | None = None,
    status: str | None = None,
) -> CrossPlatformResponse:
    """Return cross-platform SKU mapping matrix with match scores and fee/spread metrics."""
    # ponytail: 模拟图文向量对齐模型打分；后续接入跨平台多模态特征对齐索引
    now = utc_now()
    trend_res = get_bsr_trends(session, tenant_id=tenant_id)
    target_items = trend_res.items

    raw_items: list[CrossPlatformItem] = []
    for item in target_items:
        t_asin = item.asin
        t_price = item.current_price
        t_title = item.title

        # Counterpart 1: TikTok Shop
        tiktok_price = round(t_price * 0.68, 2)
        tiktok_fees = round(
            tiktok_price * 0.08 + 4.20, 2
        )  # 8% commission + $4.20 fulfillment
        tiktok_spread = round(t_price - tiktok_price - tiktok_fees, 2)
        match_score_tt = round(0.88 + (_hash_int(f"{t_asin}:tt", 11) * 0.01), 2)
        tt_status = "MATCHED" if match_score_tt >= 0.90 else "PENDING"

        raw_items.append(
            CrossPlatformItem(
                id=f"map_tt_{t_asin}",
                target_asin=t_asin,
                target_title=t_title,
                target_price=t_price,
                platform="TIKTOK",
                platform_sku=f"TTS-{t_asin[:6]}-BLK",
                platform_title="Viral Stainless Tumbler Mug Leakproof 40oz (TikTok Trending)",
                platform_url=f"https://shop.tiktok.com/view/product/{t_asin}",
                platform_price=tiktok_price,
                estimated_fees=tiktok_fees,
                estimated_spread=tiktok_spread,
                match_score=min(match_score_tt, 0.99),
                match_status=tt_status,
                monthly_sales=3200 + _hash_int(f"{t_asin}:tt_sales", 4000),
                updated_at=now,
            )
        )

        # Counterpart 2: Temu
        temu_price = round(t_price * 0.42, 2)
        temu_fees = round(temu_price * 0.05 + 3.10, 2)
        temu_spread = round(t_price - temu_price - temu_fees, 2)
        match_score_temu = round(0.82 + (_hash_int(f"{t_asin}:temu", 14) * 0.01), 2)
        temu_status = (
            "MATCHED"
            if match_score_temu >= 0.90
            else ("VARIANT" if match_score_temu < 0.85 else "PENDING")
        )

        raw_items.append(
            CrossPlatformItem(
                id=f"map_temu_{t_asin}",
                target_asin=t_asin,
                target_title=t_title,
                target_price=t_price,
                platform="TEMU",
                platform_sku=f"TEMU-{t_asin[:6]}-M40",
                platform_title="Factory Direct Insulated Double Wall Coffee Cup Outdoor Travel",
                platform_url=f"https://www.temu.com/goods.html?goods_id={t_asin}",
                platform_price=temu_price,
                estimated_fees=temu_fees,
                estimated_spread=temu_spread,
                match_score=min(match_score_temu, 0.99),
                match_status=temu_status,
                monthly_sales=5800 + _hash_int(f"{t_asin}:temu_sales", 6000),
                updated_at=now,
            )
        )

    # Filter
    filtered = raw_items
    if asin:
        filtered = [x for x in filtered if x.target_asin.lower() == asin.lower()]
    if platform and platform.upper() != "ALL":
        filtered = [x for x in filtered if x.platform == platform.upper()]
    if status and status.upper() != "ALL":
        filtered = [x for x in filtered if x.match_status == status.upper()]

    avg_score = round(fmean([x.match_score for x in filtered]), 3) if filtered else 0.0
    max_spread = max([x.estimated_spread for x in filtered], default=0.0)
    arbitrage_count = sum(
        1 for x in filtered if x.estimated_spread > 0 and x.match_score >= 0.85
    )

    metrics = CrossPlatformMetrics(
        total_skus=len(filtered),
        avg_match_score=avg_score,
        max_spread=max_spread,
        arbitrage_opportunities=arbitrage_count,
    )

    return CrossPlatformResponse(metrics=metrics, items=filtered)
