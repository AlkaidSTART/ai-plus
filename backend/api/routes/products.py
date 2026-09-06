"""Product & review routes (docs/api.md §6, §7.1)."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from api.errors import ApiError, ErrorCode
from api.schemas.common import Envelope, PageData
from api.schemas.product import ProductDetailOut, ProductOut, ReviewOut
from db.repositories.review_repository import ProductRepository, ReviewRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])


def _product_to_out(row) -> ProductOut:
    return ProductOut(
        product_id=str(row.id),
        asin=row.asin,
        platform=row.platform,
        marketplace=row.marketplace,
        title=row.title,
        category=row.category,
        current_price=float(row.current_price) if row.current_price is not None else None,
        currency=row.currency or "USD",
        main_image_url=row.main_image_url,
        review_count=row.review_count,
        avg_rating=float(row.avg_rating) if row.avg_rating is not None else None,
        bsr=row.bsr,
        updated_at=row.updated_at,
    )


@router.get("", response_model=Envelope[PageData[ProductOut]])
async def list_products(
    platform: str | None = Query(default=None),
    marketplace: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> Envelope[PageData[ProductOut]]:
    from sqlalchemy import func, select
    from db.models import Product

    try:
        stmt = select(Product)
        if platform:
            stmt = stmt.where(Product.platform == platform)
        if marketplace:
            stmt = stmt.where(Product.marketplace == marketplace)
        if keyword:
            stmt = stmt.where(
                Product.title.ilike(f"%{keyword}%") | Product.asin.ilike(f"%{keyword}%")
            )
        total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (
            await session.scalars(
                stmt.order_by(Product.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    except Exception:  # noqa: BLE001 - DB 不可用时如实返回空结果
        logger.warning("products list: database unavailable", exc_info=True)
        return Envelope(data=PageData[ProductOut](items=[], total=0, page=page, page_size=page_size))

    return Envelope(
        data=PageData[ProductOut](
            items=[_product_to_out(r) for r in rows],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )
    )


async def _get_product_or_404(session: AsyncSession, product_id: str):
    row = await ProductRepository(session).get(product_id)
    if row is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"商品不存在: {product_id}")
    return row


@router.get("/{product_id}", response_model=Envelope[ProductDetailOut])
async def product_detail(
    product_id: str, session: AsyncSession = Depends(get_db)
) -> Envelope[ProductDetailOut]:
    try:
        row = await _get_product_or_404(session, product_id)
    except ApiError:
        raise
    except Exception:  # noqa: BLE001
        logger.warning("product detail: database unavailable", exc_info=True)
        raise ApiError(ErrorCode.NOT_FOUND, f"商品不存在或数据源不可用: {product_id}")
    return Envelope(
        data=ProductDetailOut(
            **_product_to_out(row).model_dump(),
            length_cm=float(row.length_cm) if row.length_cm is not None else None,
            width_cm=float(row.width_cm) if row.width_cm is not None else None,
            height_cm=float(row.height_cm) if row.height_cm is not None else None,
            weight_kg=float(row.weight_kg) if row.weight_kg is not None else None,
            bsr_category=row.bsr_category,
            created_at=row.created_at,
        )
    )


@router.get("/{product_id}/price-history")
async def price_history(product_id: str) -> Envelope[dict]:
    # P1：当前无正式价格历史数据源（禁止伪造时序），明确功能不可用
    raise ApiError(ErrorCode.UPSTREAM, "价格/BSR/Buy Box 历史数据源尚未接入，功能暂不可用")


@router.get("/{product_id}/reviews", response_model=Envelope[PageData[ReviewOut]])
async def product_reviews(
    product_id: str,
    rating_min: float | None = Query(default=None, ge=0, le=5),
    rating_max: float | None = Query(default=None, ge=0, le=5),
    language: str | None = Query(default=None),
    verified_only: bool | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> Envelope[PageData[ReviewOut]]:
    try:
        product = await _get_product_or_404(session, product_id)
        rows, total = await ReviewRepository(session).list_for_product(
            product.id,
            rating_min=rating_min,
            rating_max=rating_max,
            language=language,
            verified_only=verified_only,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
    except ApiError:
        raise
    except Exception:  # noqa: BLE001
        logger.warning("product reviews: database unavailable", exc_info=True)
        raise ApiError(ErrorCode.NOT_FOUND, f"商品不存在或数据源不可用: {product_id}")

    items = [
        ReviewOut(
            review_id=r.external_review_id,
            rating=float(r.rating),
            review_date=r.review_date,
            language=r.original_language or "en",
            title=r.title,
            content=r.content,
            translated_content=r.translated_content,
            verified_purchase=bool(r.verified_purchase),
            helpful_votes=r.helpful_votes or 0,
            image_urls=[img.storage_url for img in r.images] if r.images else [],
        )
        for r in rows
    ]
    return Envelope(
        data=PageData[ReviewOut](items=items, total=total, page=page, page_size=page_size)
    )
