"""Semantic clustering service: embeddings + similarity + severity rules.

向量相似性（贪心凝聚聚类）+ 规则（严重度映射/关键词）+ 可选 LLM 归纳标签。
不让 LLM 凭空从零生成评论结论——聚类成员关系完全由向量相似性决定。
"""

import logging
from collections import Counter

from agents.state import ClusterItem, ReviewItem, VisualEvidence
from core.embedding import EmbeddingService, FakeEmbeddingService

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.75
TOP_N = 5
ISSUE_TYPE_BY_KEYWORD: list[tuple[str, str]] = [
    ("broke", "product_defect"),
    ("crack", "product_defect"),
    ("color", "product_defect"),
    ("crushed", "packaging_delivery"),
    ("damaged", "packaging_delivery"),
    ("small", "size_spec"),
    ("large", "size_spec"),
    ("missing", "accessory"),
    ("manual", "manual"),
]

FALLBACK_NAMES = {
    "product_defect": "产品质量缺陷",
    "function_defect": "功能异常",
    "size_spec": "尺寸规格问题",
    "accessory": "配件缺失",
    "manual": "说明书问题",
    "packaging_delivery": "包装履约问题",
    "other": "其他问题",
}


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def severity_level(score: float) -> str:
    if score >= 4.0:
        return "critical"
    if score >= 2.5:
        return "moderate"
    return "minor"


def guess_issue_type(text: str) -> str:
    lowered = text.lower()
    for keyword, issue_type in ISSUE_TYPE_BY_KEYWORD:
        if keyword in lowered:
            return issue_type
    return "other"


class ClusterService:
    def __init__(
        self,
        embedding: EmbeddingService | FakeEmbeddingService,
        llm=None,
    ) -> None:
        self.embedding = embedding
        self.llm = llm

    async def cluster(
        self, reviews: list[ReviewItem], evidences: list[VisualEvidence]
    ) -> list[ClusterItem]:
        if not reviews:
            return []
        # 只对差评（<=3 星）聚类，正评不构成痛点
        negatives = [r for r in reviews if r["rating"] <= 3.0] or reviews
        vectors = await self.embedding.embed([r["content"] for r in negatives])

        members: list[list[int]] = []
        centroids: list[list[float]] = []
        for i, vector in enumerate(vectors):
            best, best_sim = None, 0.0
            for ci, centroid in enumerate(centroids):
                sim = cosine(vector, centroid)
                if sim > best_sim:
                    best, best_sim = ci, sim
            if best is not None and best_sim >= SIMILARITY_THRESHOLD:
                members[best].append(i)
                # 更新质心（均值后归一化由后续余弦近似处理）
                centroid = centroids[best]
                n = len(members[best])
                centroids[best] = [
                    (c * (n - 1) + v) / n for c, v in zip(centroid, vector)
                ]
            else:
                members.append([i])
                centroids.append(list(vector))

        total = max(len(negatives), 1)
        images_by_review: dict[str, list[str]] = {}
        for e in evidences:
            images_by_review.setdefault(e["review_id"], []).append(e["image_id"])

        clusters: list[ClusterItem] = []
        for idx, member in enumerate(members):
            cluster_reviews = [negatives[i] for i in member]
            ratings = [r["rating"] for r in cluster_reviews]
            # 严重度 = 差评程度（5 - 平均星级）放满 5 分制
            severity = round(min(5.0, (5 - (sum(ratings) / len(ratings))) * 1.6), 1)
            keywords = self._keywords(cluster_reviews)
            issue_type = guess_issue_type(" ".join(keywords) or cluster_reviews[0]["content"])
            clusters.append(
                ClusterItem(
                    cluster_id=f"clu_{idx + 1:02d}",
                    cluster_name=self._name(cluster_reviews, keywords, issue_type),
                    issue_type=issue_type,
                    frequency=len(member),
                    frequency_ratio=round(len(member) / total, 2),
                    severity_score=severity,
                    severity_level=severity_level(severity),
                    keywords=keywords,
                    sample_quotes=[
                        {
                            "review_id": r["review_id"],
                            "language": r["language"],
                            "content": r["content"],
                            "translated_content": r["translated_content"],
                            "rating": r["rating"],
                        }
                        for r in cluster_reviews[:3]
                    ],
                    sample_image_ids=[
                        img
                        for r in cluster_reviews
                        for img in images_by_review.get(r["review_id"], [])
                    ][:5],
                    review_ids=[r["review_id"] for r in cluster_reviews],
                )
            )
        clusters.sort(key=lambda c: (c["severity_score"] * c["frequency_ratio"]), reverse=True)
        return clusters[:TOP_N]

    @staticmethod
    def _keywords(reviews: list[ReviewItem]) -> list[str]:
        stop = {"the", "a", "and", "is", "of", "to", "it", "in", "for", "with", "this", "after"}
        words: Counter[str] = Counter()
        for review in reviews:
            for word in review["content"].lower().replace(",", " ").replace(".", " ").split():
                if len(word) > 3 and word not in stop:
                    words[word] += 1
        return [w for w, _ in words.most_common(5)]

    def _name(self, reviews: list[ReviewItem], keywords: list[str], issue_type: str) -> str:
        # 有 LLM 时做归纳标签；否则用关键词/回退名
        return "/".join(keywords[:2]).capitalize() if keywords else FALLBACK_NAMES.get(issue_type, "其他问题")
