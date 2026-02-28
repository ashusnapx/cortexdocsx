"""
WHAT: BM25 index manager for keyword-based retrieval.
WHY: BM25 captures exact keyword matches that semantic embeddings miss.
     Combined with vector search in hybrid retrieval for best-of-both-worlds.
WHEN: Rebuilt during ingestion. Queried during hybrid retrieval.
WHERE: backend/app/infrastructure/bm25_store.py
HOW: rank_bm25 library with pickle persistence.
ALTERNATIVES CONSIDERED:
  - Elasticsearch: Heavy infrastructure for local dev.
  - Whoosh: Less maintained, slower than rank_bm25 for this scale.
  - Custom TF-IDF: rank_bm25 is more sophisticated (Okapi BM25).
TRADEOFFS:
  - Full rebuild on each ingestion — acceptable for <100k chunks.
  - In-memory only during runtime — loaded from disk on startup.
  - No incremental add — must rebuild from all chunks. Mitigated by fast rebuild time.
"""

import pickle
import re
from pathlib import Path
from typing import Optional

import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class BM25StoreManager:
    """
    WHAT: Manages BM25 index for keyword-based retrieval.
    WHY: Complements vector search in the hybrid retrieval pipeline.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._index = None
        self._index_dir = Path(self._settings.BM25_INDEX_DIR)
        self._corpus: list[list[str]] = []
        self._chunk_ids: list[int] = []
        self._total_documents: int = 0

    @property
    def is_loaded(self) -> bool:
        return self._index is not None

    @property
    def total_documents(self) -> int:
        return self._total_documents

    async def initialize(self) -> None:
        """
        WHAT: Initialize or load the BM25 index from disk.
        WHY: Called at app startup. Loads persisted index or starts empty.
        """
        self._index_dir.mkdir(parents=True, exist_ok=True)
        index_path = self._index_dir / "bm25_index.pkl"

        if index_path.exists():
            try:
                with open(index_path, "rb") as f:
                    data = pickle.load(f)
                    self._index = data["index"]
                    self._corpus = data["corpus"]
                    self._chunk_ids = data["chunk_ids"]
                    self._total_documents = len(self._corpus)
                logger.info(
                    "bm25_index_loaded",
                    total_documents=self._total_documents,
                )
            except Exception as e:
                logger.error("bm25_index_load_failed", error=str(e))
                self._index = None
                self._corpus = []
                self._chunk_ids = []
        else:
            logger.info("bm25_index_empty_start")

    async def rebuild(
        self, texts: list[str], chunk_ids: list[int]
    ) -> None:
        """
        WHAT: Rebuild the entire BM25 index from a corpus of texts.
        WHY: Called after ingestion. BM25 doesn't support incremental adds cleanly.
        HOW: Tokenizes all texts and builds the BM25Okapi index.
        """
        from rank_bm25 import BM25Okapi

        self._corpus = [self._tokenize(text) for text in texts]
        self._chunk_ids = chunk_ids

        if self._corpus:
            self._index = BM25Okapi(self._corpus)
        else:
            self._index = None

        self._total_documents = len(self._corpus)
        logger.info("bm25_index_rebuilt", total_documents=self._total_documents)

    async def search(
        self, query: str, top_k: int = 20
    ) -> tuple[list[int], list[float]]:
        """
        WHAT: Search the BM25 index for relevant chunks.
        WHY: Keyword-based retrieval component of hybrid search.
        Returns: (list of chunk vector_store_ids, list of BM25 scores)
        """
        if self._index is None or not self._corpus:
            return [], []

        tokenized_query = self._tokenize(query)
        scores = self._index.get_scores(tokenized_query)

        # Get top-k indices sorted by score descending
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:top_k]

        result_ids = []
        result_scores = []

        for idx in top_indices:
            if scores[idx] > 0:
                result_ids.append(self._chunk_ids[idx])
                result_scores.append(float(scores[idx]))

        return result_ids, result_scores

    async def persist(self) -> str:
        """
        WHAT: Save the BM25 index to disk.
        WHY: Persistence across restarts.
        """
        index_path = self._index_dir / "bm25_index.pkl"
        with open(index_path, "wb") as f:
            pickle.dump(
                {
                    "index": self._index,
                    "corpus": self._corpus,
                    "chunk_ids": self._chunk_ids,
                },
                f,
            )
        logger.info("bm25_index_persisted", path=str(index_path))
        return str(index_path)

    async def health_check(self) -> dict:
        """
        WHAT: Report BM25 index health status.
        WHY: Exposed via health endpoint.
        """
        return {
            "status": "ok" if self._index is not None else "empty",
            "total_documents": self._total_documents,
        }

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """
        WHAT: Simple whitespace + lowercase tokenizer.
        WHY: BM25Okapi expects tokenized input. Simple tokenization is sufficient
             for BM25's statistical matching — it doesn't need NLP-grade tokenization.
        """
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = text.split()
        return [t for t in tokens if len(t) > 1]
