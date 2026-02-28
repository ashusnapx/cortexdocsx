"""
WHAT: Embedding generation service wrapping sentence-transformers BGE-small.
WHY: Converts text chunks into dense vector representations for semantic search.
     BGE-small-en-v1.5 offers excellent quality-to-size ratio (33M params, 384 dim).
WHEN: Called during ingestion (batch embed chunks) and query time (embed query).
WHERE: backend/app/services/embedding_service.py
HOW: Lazy-loaded singleton model. Batch encoding with configurable batch size.
     LRU cache for query embeddings to avoid recomputing repeated queries.
ALTERNATIVES CONSIDERED:
  - OpenAI text-embedding-3-small: API cost, latency, vendor dependency.
  - all-MiniLM-L6-v2: Lower quality than BGE-small on retrieval benchmarks.
  - E5-small: Comparable but less community adoption.
TRADEOFFS:
  - Model download (~130MB) on first use — one-time cost.
  - CPU inference is slower than GPU — acceptable for local dev workloads.
  - Lazy loading means first call has model load latency (~3-5s).
"""

import hashlib
from collections import OrderedDict
from typing import Optional

import numpy as np
import structlog

from app.core.config import get_settings
from app.core.features import get_feature_flags

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """
    WHAT: Service for generating text embeddings using sentence-transformers.
    WHY: Encapsulates model lifecycle (lazy load, cache) and batch encoding.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None
        self._model_name = self._settings.EMBEDDING_MODEL_NAME
        self._batch_size = self._settings.EMBEDDING_BATCH_SIZE
        self._dimension = self._settings.EMBEDDING_DIMENSION
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._cache_max_size = self._settings.CACHE_EMBEDDING_MAX_SIZE

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def memory_usage_mb(self) -> float:
        """Estimate model memory footprint."""
        if self._model is None:
            return 0.0
        # BGE-small-en-v1.5 is ~130MB in memory
        return 130.0

    async def initialize(self) -> None:
        """
        WHAT: Lazy-load the sentence-transformers model.
        WHY: Deferred loading prevents slow app startup. Only loads when first needed.
        """
        if self._model is not None:
            return

        from sentence_transformers import SentenceTransformer

        logger.info("embedding_model_loading", model=self._model_name)
        self._model = SentenceTransformer(self._model_name)
        logger.info(
            "embedding_model_loaded",
            model=self._model_name,
            dimension=self._dimension,
        )

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        WHAT: Batch encode a list of texts into embeddings.
        WHY: Used during ingestion to embed all chunks efficiently.
        HOW: sentence-transformers encode() with configurable batch_size.
        Returns: numpy array of shape (len(texts), dimension).
        """
        if self._model is None:
            await self.initialize()

        embeddings = self._model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=self._settings.EMBEDDING_NORMALIZE,
            show_progress_bar=False,
        )

        logger.info("embeddings_generated", count=len(texts))
        return np.array(embeddings, dtype=np.float32)

    async def embed_query(self, query: str) -> np.ndarray:
        """
        WHAT: Encode a single query into an embedding vector.
        WHY: Used at query time for vector similarity search.
        HOW: Checks LRU cache first, computes if miss.
        """
        flags = get_feature_flags()

        if flags.ENABLE_EMBEDDING_CACHE:
            cache_key = self._cache_key(query)
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                logger.debug("embedding_cache_hit", query_hash=cache_key[:8])
                return self._cache[cache_key]

        embedding = await self.embed_texts([query])
        result = embedding[0]

        if flags.ENABLE_EMBEDDING_CACHE:
            self._cache_put(cache_key, result)

        return result

    def _cache_key(self, text: str) -> str:
        """Generate a deterministic cache key for a text."""
        return hashlib.sha256(text.encode()).hexdigest()

    def _cache_put(self, key: str, value: np.ndarray) -> None:
        """Insert into LRU cache, evicting oldest if at capacity."""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._cache_max_size:
                self._cache.popitem(last=False)
            self._cache[key] = value

    async def health_check(self) -> dict:
        return {
            "status": "ok" if self._model is not None else "not_loaded",
            "model": self._model_name,
            "dimension": self._dimension,
            "cache_size": len(self._cache),
            "memory_usage_mb": self.memory_usage_mb,
        }
