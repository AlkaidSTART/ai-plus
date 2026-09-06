"""Vision audit service (Claude Vision over buyer photos).

失败降级：Vision 不可用或调用失败时返回空取证列表并记录 warning，
绝不阻断文本主链路（docs Step 3 §六）。
"""

import base64
import logging

from agents.state import ReviewItem, VisualEvidence
from core.llm import LLMClient, LLMError

logger = logging.getLogger(__name__)

DEFECT_CATEGORIES = {"color_difference", "broken_package", "craft_flaw", "dimension_issue", "other"}

VISION_PROMPT = """You are a product defect auditor for cross-border e-commerce.
Analyze the attached buyer photo. Reply ONLY with JSON:
{{"defect_category": "color_difference|broken_package|craft_flaw|dimension_issue|other",
"description": "一句话中文缺陷描述", "confidence": 0.0-1.0,
"bbox": [x0, y0, x1, y1] or null}}"""


class VisionAuditService:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def audit(self, reviews: list[ReviewItem]) -> list[VisualEvidence]:
        images = [
            (review, url) for review in reviews for url in review.get("image_urls", [])
        ]
        if not images:
            return []
        if self.llm is None:
            logger.warning("vision: LLM 未配置，降级为纯文本分析（跳过 %d 张图）", len(images))
            return []

        evidences: list[VisualEvidence] = []
        for index, (review, url) in enumerate(images):
            try:
                analysis = await self._analyze(url)
                evidences.append(
                    VisualEvidence(
                        image_id=f"img_{index:04d}",
                        review_id=review["review_id"],
                        storage_url=url,
                        defect_category=analysis.get("defect_category", "other"),
                        description=analysis.get("description", ""),
                        confidence=float(analysis.get("confidence", 0.0)),
                        bbox=analysis.get("bbox") or [0, 0, 0, 0],
                        cluster_ids=[],
                    )
                )
            except (LLMError, Exception) as exc:  # noqa: BLE001 - degrade, don't fail
                logger.warning("vision: 单图分析失败已降级 (%s): %s", url, exc)
        return evidences

    async def _analyze(self, image_url: str) -> dict:
        import httpx

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            image_bytes = resp.content
        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        message = [
            {"type": "text", "text": VISION_PROMPT},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": content_type,
                    "data": base64.b64encode(image_bytes).decode(),
                },
            },
        ]
        text = await self.llm.complete_messages(message)
        from core.llm import extract_json

        return extract_json(text)
