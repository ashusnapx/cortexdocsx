"""
WHAT: Cross-encoder reranking service using BGE-reranker-base.
WHY: Cross-encoders jointly encode query+document pairs, producing far more accurate
     relevance scores than bi-encoder cosine similarity. Dramatically improves
     retrieval precision at a small latency cost (~200ms for top-10).
WHEN: Called after hybrid retrieval to refine the top-K candidates.
WHERE: backend/app/services/reranking_service.py
HOW: Lazy-loaded CrossEncoder model. Scores query-chunk pairs and re-sorts by score.
ALTERNATIVES CONSIDERED:
  - Cohere Rerank API: API cost, network latency, vendor lock-in.
  - ColBERT: More complex, requires special indexing infrastructure.
  - No reranking: Significantly lower retrieval precision.
TRADEOFFS:
  - ~1.1GB model download on first use.
  - ~200ms latency per reranking pass — justified by precision gains.
  - CPU inference — GPU would be 10x faster but not required for local dev.
"""

from typing import Optional

import numpy as np
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class RerankingService:
    """
    WHAT: Cross-encoder reranking for refining retrieval results.
    WHY: Joint query-document scoring produces much better relevance judgments.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None
        self._model_name = self._settings.RERANKER_MODEL_NAME
        self._batch_size = self._settings.RERANKER_BATCH_SIZE

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    async def initialize(self) -> None:
        """
        WHAT: Lazy-load the cross-encoder reranker model.
        WHY: ~1.1GB model — defer loading until first reranking request.
        """
        if self._model is not None:
            return

        from sentence_transformers import CrossEncoder

        logger.info("reranker_model_loading", model=self._model_name)
        self._model = CrossEncoder(self._model_name)
        logger.info("reranker_model_loaded", model=self._model_name)

    async def rerank(
        self, query: str, chunks: list[dict], top_k: Optional[int] = None
    ) -> list[dict]:
        """
        WHAT: Rerank chunks by cross-encoder relevance score.
        WHY: Produces a more accurate ranking than the initial hybrid retrieval.

        Args:
            query: User query string.
            chunks: List of chunk dicts with at least 'content' key.
            top_k: Number of top results to return (None = return all).

        Returns:
            Reranked list of chunks with added 'reranker_score' field.
        """
        if self._model is None:
            await self.initialize()

        if not chunks:
            return []

        # Create query-document pairs for the cross-encoder
        pairs = [[query, chunk["content"]] for chunk in chunks]

        # Score all pairs
        scores = self._model.predict(pairs, batch_size=self._batch_size)

        # Normalize scores to [0, 1] using sigmoid
        normalized_scores = 1.0 / (1.0 + np.exp(-np.array(scores)))

        # Attach scores and sort
        for chunk, score in zip(chunks, normalized_scores):
            chunk["reranker_score"] = float(score)

        reranked = sorted(chunks, key=lambda c: c["reranker_score"], reverse=True)

        if top_k is not None:
            reranked = reranked[:top_k]

        logger.info(
            "reranking_completed",
            input_count=len(chunks),
            output_count=len(reranked),
            top_score=round(reranked[0]["reranker_score"], 4) if reranked else 0.0,
        )

        return reranked
