"""
WHAT: Chunk repository for chunk table operations.
WHY: Isolates chunk DB access from service logic. Enables batch operations
     and efficient retrieval by document or vector store IDs.
WHEN: Used by IngestionService (bulk create) and RetrievalService (lookup by IDs).
WHERE: backend/app/repositories/chunk_repo.py
HOW: Extends BaseRepository with chunk-specific batch and lookup operations.
ALTERNATIVES CONSIDERED: N/A — repository pattern.
TRADEOFFS: Batch insert uses add_all which is less efficient than COPY but simpler.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Chunk
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    """
    WHAT: Repository for Chunk CRUD and batch operations.
    WHY: Chunks are the primary retrieval unit — efficient access is critical.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Chunk)

    async def get_by_document_id(self, document_id: UUID) -> Sequence[Chunk]:
        """
        WHAT: Fetch all chunks for a specific document.
        WHY: Used for document detail view and re-indexing.
        """
        stmt = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_vector_store_ids(
        self, vector_store_ids: list[int]
    ) -> Sequence[Chunk]:
        """
        WHAT: Fetch chunks by their FAISS vector store IDs.
        WHY: After FAISS search returns IDs, we need the actual chunk content.
        """
        if not vector_store_ids:
            return []
        stmt = (
            select(Chunk)
            .options(selectinload(Chunk.document))
            .where(Chunk.vector_store_id.in_(vector_store_ids))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_ids(self, chunk_ids: list[UUID]) -> Sequence[Chunk]:
        """
        WHAT: Fetch chunks by their UUIDs.
        WHY: Used for query replay and citation rendering.
        """
        if not chunk_ids:
            return []
        stmt = (
            select(Chunk)
            .options(selectinload(Chunk.document))
            .where(Chunk.id.in_(chunk_ids))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def bulk_create(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        WHAT: Insert multiple chunks in a single transaction.
        WHY: Document ingestion produces many chunks — batch insert is significantly faster.
        """
        self._session.add_all(chunks)
        await self._session.flush()
        return chunks

    async def delete_by_document_id(self, document_id: UUID) -> int:
        """
        WHAT: Delete all chunks for a document.
        WHY: Used during document re-ingestion or deletion.
        """
        stmt = select(Chunk).where(Chunk.document_id == document_id)
        result = await self._session.execute(stmt)
        chunks = result.scalars().all()
        count = len(chunks)
        for chunk in chunks:
            await self._session.delete(chunk)
        await self._session.flush()
        return count

    async def get_all_for_indexing(self) -> Sequence[Chunk]:
        """
        WHAT: Fetch all chunks for full index rebuild.
        WHY: Used when rebuilding FAISS/BM25 indexes from scratch.
        """
        stmt = (
            select(Chunk)
            .options(selectinload(Chunk.document))
            .order_by(Chunk.vector_store_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
