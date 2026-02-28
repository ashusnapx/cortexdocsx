"""
WHAT: FAISS vector store manager with versioned persistence and snapshotting.
WHY: FAISS provides zero-cost, low-latency vector similarity search locally.
     Versioning enables rollback to previous index states after bad ingestions.
WHEN: Loaded at app startup. Updated during ingestion. Queried during retrieval.
WHERE: backend/app/infrastructure/vector_store.py
HOW: FAISS IndexFlatIP (inner product for normalized embeddings = cosine similarity).
     Persisted to disk with version tagging.
ALTERNATIVES CONSIDERED:
  - Pinecone: SaaS cost, network latency, vendor lock-in.
  - Milvus: Heavy infrastructure for local dev.
  - ChromaDB: Less mature, fewer tuning options than FAISS.
  - Weaviate: Requires separate server process.
TRADEOFFS:
  - FAISS is single-node only — no distributed scaling.
  - IndexFlatIP does brute-force search — O(n) but fast enough for <1M vectors.
  - No built-in metadata filtering — handled via post-retrieval DB lookup.
  - Manual backup needed — mitigated by versioned snapshotting.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

import numpy as np
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class VectorStoreManager:
    """
    WHAT: Manages FAISS index lifecycle: create, add, search, persist, snapshot.
    WHY: Encapsulates all vector store operations behind a clean interface.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._index = None
        self._index_dir = Path(self._settings.FAISS_INDEX_DIR)
        self._dimension = self._settings.EMBEDDING_DIMENSION
        self._current_version: int = 0
        self._total_vectors: int = 0

    @property
    def is_loaded(self) -> bool:
        return self._index is not None

    @property
    def total_vectors(self) -> int:
        if self._index is not None:
            return self._index.ntotal
        return 0

    @property
    def current_version(self) -> int:
        return self._current_version

    @property
    def memory_usage_mb(self) -> float:
        """
        WHAT: Estimate memory usage of the FAISS index.
        WHY: Exposed to health endpoint for infrastructure awareness.
        HOW: vectors * dimension * 4 bytes (float32).
        """
        if self._index is None:
            return 0.0
        return (self._index.ntotal * self._dimension * 4) / (1024 * 1024)

    async def initialize(self) -> None:
        """
        WHAT: Initialize or load the FAISS index.
        WHY: Called at app startup. Loads persisted index or creates new one.
        """
        import faiss

        self._index_dir.mkdir(parents=True, exist_ok=True)
        active_path = self._index_dir / "active_index.faiss"

        if active_path.exists():
            try:
                self._index = faiss.read_index(str(active_path))
                self._total_vectors = self._index.ntotal
                logger.info(
                    "faiss_index_loaded",
                    path=str(active_path),
                    total_vectors=self._total_vectors,
                    memory_mb=round(self.memory_usage_mb, 2),
                )
            except Exception as e:
                logger.error("faiss_index_load_failed", error=str(e))
                self._index = faiss.IndexFlatIP(self._dimension)
                logger.info("faiss_index_created_fresh", dimension=self._dimension)
        else:
            self._index = faiss.IndexFlatIP(self._dimension)
            logger.info("faiss_index_created_fresh", dimension=self._dimension)

    async def add_vectors(
        self, vectors: np.ndarray, start_id: Optional[int] = None
    ) -> list[int]:
        """
        WHAT: Add vectors to the FAISS index.
        WHY: Called during ingestion after embedding generation.
        HOW: Vectors must be float32 and normalized for cosine similarity via IP.
        Returns: List of assigned vector IDs (sequential from current ntotal).
        """
        import faiss

        if self._index is None:
            raise RuntimeError("Vector store not initialized")

        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        vectors = vectors.astype(np.float32)

        # Normalize for cosine similarity via inner product
        faiss.normalize_L2(vectors)

        start = self._index.ntotal
        self._index.add(vectors)

        ids = list(range(start, start + len(vectors)))
        self._total_vectors = self._index.ntotal

        logger.info(
            "vectors_added",
            count=len(vectors),
            total=self._total_vectors,
            start_id=start,
        )

        return ids

    async def search(
        self, query_vector: np.ndarray, top_k: int = 20
    ) -> tuple[list[int], list[float]]:
        """
        WHAT: Search for nearest neighbors in the FAISS index.
        WHY: Core vector retrieval operation.
        Returns: (list of vector IDs, list of similarity scores)
        """
        import faiss

        if self._index is None or self._index.ntotal == 0:
            return [], []

        query = query_vector.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(query)

        actual_k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query, actual_k)

        # Filter out -1 indices (FAISS returns -1 for empty slots)
        valid_results = [
            (int(idx), float(score))
            for idx, score in zip(indices[0], scores[0])
            if idx >= 0
        ]

        ids = [r[0] for r in valid_results]
        sim_scores = [r[1] for r in valid_results]

        return ids, sim_scores

    async def persist(self) -> str:
        """
        WHAT: Save the current index to disk.
        WHY: Persistence across restarts. Called after ingestion completes.
        Returns: Path to the saved index file.
        """
        import faiss

        if self._index is None:
            raise RuntimeError("Vector store not initialized")

        active_path = self._index_dir / "active_index.faiss"
        faiss.write_index(self._index, str(active_path))

        logger.info(
            "faiss_index_persisted",
            path=str(active_path),
            total_vectors=self._total_vectors,
        )
        return str(active_path)

    async def snapshot(self, version: int) -> str:
        """
        WHAT: Create a versioned snapshot of the current index.
        WHY: Enables rollback to previous index state after bad ingestions.
        Returns: Path to the snapshot file.
        """
        import faiss

        if self._index is None:
            raise RuntimeError("Vector store not initialized")

        snapshot_path = self._index_dir / f"vector_index_v{version}.faiss"
        faiss.write_index(self._index, str(snapshot_path))
        self._current_version = version

        logger.info(
            "faiss_index_snapshot_created",
            version=version,
            path=str(snapshot_path),
            total_vectors=self._total_vectors,
        )
        return str(snapshot_path)

    async def rollback(self, version: int) -> bool:
        """
        WHAT: Rollback to a previous index version.
        WHY: Recovery mechanism if a bad document batch corrupts the index.
        Returns: True if rollback succeeded.
        """
        import faiss

        snapshot_path = self._index_dir / f"vector_index_v{version}.faiss"
        if not snapshot_path.exists():
            logger.error("faiss_rollback_failed", version=version, reason="snapshot not found")
            return False

        self._index = faiss.read_index(str(snapshot_path))
        self._total_vectors = self._index.ntotal
        self._current_version = version

        # Copy to active
        active_path = self._index_dir / "active_index.faiss"
        shutil.copy2(str(snapshot_path), str(active_path))

        logger.info(
            "faiss_index_rolled_back",
            version=version,
            total_vectors=self._total_vectors,
        )
        return True

    async def rebuild(self, vectors: np.ndarray) -> None:
        """
        WHAT: Rebuild the entire index from scratch.
        WHY: Used when embedding model changes or chunking parameters change.
        """
        import faiss

        self._index = faiss.IndexFlatIP(self._dimension)
        if len(vectors) > 0:
            vectors = vectors.astype(np.float32)
            faiss.normalize_L2(vectors)
            self._index.add(vectors)

        self._total_vectors = self._index.ntotal
        logger.info("faiss_index_rebuilt", total_vectors=self._total_vectors)

    async def health_check(self) -> dict:
        """
        WHAT: Report vector store health status.
        WHY: Exposed via health endpoint.
        """
        return {
            "status": "ok" if self._index is not None else "unavailable",
            "total_vectors": self.total_vectors,
            "dimension": self._dimension,
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "current_version": self._current_version,
        }
