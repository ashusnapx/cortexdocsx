"""
WHAT: Hybrid retrieval service combining vector search and BM25.
WHY: Vector search captures semantic similarity. BM25 captures exact keyword matches.
     Combining both yields better recall than either alone — semantic understanding
     with keyword precision.
WHEN: Called during the query pipeline after intent classification.
WHERE: backend/app/services/retrieval_service.py
HOW: Executes both searches in parallel, normalizes scores, combines with alpha/beta
     weights, deduplicates, and returns ranked results.
ALTERNATIVES CONSIDERED:
  - Vector-only: Misses exact keyword matches (e.g., model numbers, codes).
  - BM25-only: Misses semantic connections (synonyms, paraphrases).
  - Reciprocal Rank Fusion: Simpler but less tunable than weighted combination.
TRADEOFFS:
  - Maintaining two indexes doubles storage and ingestion cost.
  - Alpha/beta tuning is dataset-dependent — defaults work for general use.
  - Score normalization assumes comparable distributions — robust enough in practice.
"""

from typing import Optional

import numpy as np
import structlog

from app.core.config import get_settings
from app.core.constants import BM25_SCORE_NORMALIZATION_FACTOR
from app.core.features import get_feature_flags
from app.infrastructure.bm25_store import BM25StoreManager
from app.infrastructure.vector_store import VectorStoreManager
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)


class RetrievalService:
    """
    WHAT: Hybrid retrieval combining vector similarity and BM25 keyword search.
    WHY: Best-of-both-worlds retrieval with configurable blend weights.
    """

    def __init__(
        self,
        vector_store: VectorStoreManager,
        bm25_store: BM25StoreManager,
        embedding_service: EmbeddingService,
    ) -> None:
        self._vector_store = vector_store
        self._bm25_store = bm25_store
        self._embedding_service = embedding_service
        self._settings = get_settings()

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
    ) -> list[dict]:
        """
        WHAT: Execute hybrid retrieval and return scored chunk IDs.
        WHY: Core retrieval operation for the query pipeline.

        Returns:
            List of dicts with keys: vector_store_id, vector_score, bm25_score, combined_score
        """
        flags = get_feature_flags()
        top_k = top_k or self._settings.RETRIEVAL_TOP_K
        alpha = alpha if alpha is not None else self._settings.HYBRID_ALPHA
        beta = beta if beta is not None else self._settings.HYBRID_BETA

        # Embed the query
        query_embedding = await self._embedding_service.embed_query(query)

        # Vector search
        vector_ids, vector_scores = await self._vector_store.search(query_embedding, top_k)

        # BM25 search (if enabled)
        if flags.ENABLE_HYBRID_SEARCH:
            bm25_ids, bm25_scores = await self._bm25_store.search(query, top_k)
        else:
            bm25_ids, bm25_scores = [], []
            alpha = 1.0
            beta = 0.0

        # Normalize scores
        norm_vector = self._normalize_scores(vector_scores)
        norm_bm25 = self._normalize_scores(bm25_scores)

        # Combine results with deduplication
        combined = self._combine_results(
            vector_ids, norm_vector,
            bm25_ids, norm_bm25,
            alpha, beta,
        )

        # Sort by combined score descending
        combined.sort(key=lambda x: x["combined_score"], reverse=True)
        combined = combined[:top_k]

        logger.info(
            "hybrid_retrieval_completed",
            vector_count=len(vector_ids),
            bm25_count=len(bm25_ids),
            combined_count=len(combined),
            alpha=alpha,
            beta=beta,
        )

        return combined

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        """
        WHAT: Min-max normalize scores to [0, 1] range.
        WHY: Vector and BM25 scores are on different scales — normalization
             enables meaningful weighted combination.
        """
        if not scores:
            return []
        arr = np.array(scores, dtype=np.float64)
        min_val = arr.min()
        max_val = arr.max()
        if max_val - min_val < 1e-8:
            return [1.0] * len(scores)
        normalized = (arr - min_val) / (max_val - min_val)
        return normalized.tolist()

    def _combine_results(
        self,
        vector_ids: list[int],
        vector_scores: list[float],
        bm25_ids: list[int],
        bm25_scores: list[float],
        alpha: float,
        beta: float,
    ) -> list[dict]:
        """
        WHAT: Merge vector and BM25 results with weighted combination.
        WHY: Assigns combined_score = alpha * vector_score + beta * bm25_score
             to each unique chunk, deduplicating across the two result sets.
        """
        score_map: dict[int, dict] = {}

        # Add vector results
        for vid, vscore in zip(vector_ids, vector_scores):
            score_map[vid] = {
                "vector_store_id": vid,
                "vector_score": round(vscore, 6),
                "bm25_score": 0.0,
                "combined_score": 0.0,
            }

        # Add/merge BM25 results
        for bid, bscore in zip(bm25_ids, bm25_scores):
            if bid in score_map:
                score_map[bid]["bm25_score"] = round(bscore, 6)
            else:
                score_map[bid] = {
                    "vector_store_id": bid,
                    "vector_score": 0.0,
                    "bm25_score": round(bscore, 6),
                    "combined_score": 0.0,
                }

        # Compute combined scores
        for entry in score_map.values():
            entry["combined_score"] = round(
                alpha * entry["vector_score"] + beta * entry["bm25_score"],
                6,
            )

        return list(score_map.values())
