"""Embedding service: BAAI/bge-m3, 1024-dim dense vectors.

- The model is a process-wide singleton, loaded lazily on first use and
  never reloaded per request.
- Encoding runs in a worker thread so the event loop is never blocked.
- Heavy deps (sentence-transformers / torch) are an optional extra
  (`uv sync --extra embedding`); CI and tests never download models.
- `FakeEmbeddingService` provides deterministic 1024-dim vectors offline.
"""

import asyncio
import hashlib
import logging
import math
from typing import Literal

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024
MODEL_NAME = "BAAI/bge-m3"
MAX_BATCH = 32

_model_singleton = None
_model_lock = asyncio.Lock()


def _load_model(device: str):
    global _model_singleton
    if _model_singleton is not None:
        return _model_singleton
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Embedding 依赖未安装：请执行 `uv sync --extra embedding`，"
            "或使用 FakeEmbeddingService（测试/离线模式）"
        ) from exc
    logger.info("loading embedding model %s on %s ...", MODEL_NAME, device)
    _model_singleton = SentenceTransformer(MODEL_NAME, device=device)
    return _model_singleton


class EmbeddingService:
    def __init__(self, device: str = "cpu") -> None:
        self._device = device

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = _load_model(self._device)

        def _encode() -> list[list[float]]:
            vectors: list[list[float]] = []
            for start in range(0, len(texts), MAX_BATCH):
                batch = texts[start : start + MAX_BATCH]
                result = model.encode(batch, normalize_embeddings=True)
                vectors.extend(v.tolist() for v in result)
            return vectors

        return await asyncio.to_thread(_encode)


class FakeEmbeddingService:
    """Deterministic hash-based embedding (offline tests / demo)."""

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            # Build a repeatable pseudo-random unit vector from the digest.
            raw: list[float] = []
            counter = 0
            while len(raw) < self.dim:
                seed = hashlib.sha256(digest + counter.to_bytes(4, "big")).digest()
                for i in range(0, len(seed), 4):
                    chunk = int.from_bytes(seed[i : i + 4], "big")
                    raw.append((chunk / 0xFFFFFFFF) * 2 - 1)
                    if len(raw) == self.dim:
                        break
                counter += 1
            norm = math.sqrt(sum(v * v for v in raw)) or 1.0
            vectors.append([v / norm for v in raw])
        return vectors


def build_embedding_from_settings(settings) -> EmbeddingService | FakeEmbeddingService:
    try:
        import sentence_transformers  # noqa: F401

        return EmbeddingService(device=settings.EMBEDDING_DEVICE)
    except ImportError:
        logger.warning("sentence-transformers 未安装，回退 FakeEmbeddingService（离线模式）")
        return FakeEmbeddingService()
