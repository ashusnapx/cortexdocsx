"""
WHAT: Document repository for document table operations.
WHY: Isolates all document-related DB access. Services never touch sessions directly.
WHEN: Used by IngestionService and document API routes.
WHERE: backend/app/repositories/document_repo.py
HOW: Extends BaseRepository with document-specific queries.
ALTERNATIVES CONSIDERED: N/A — repository pattern is the chosen architecture.
TRADEOFFS: Extra abstraction layer vs. direct session access — worth it for testability.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """
    WHAT: Repository for Document CRUD and document-specific queries.
    WHY: Encapsulates all document persistence logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Document)

    async def get_by_file_hash(self, file_hash: str) -> Optional[Document]:
        """
        WHAT: Find a document by its content hash.
        WHY: Deduplication — prevents re-ingesting identical files.
        """
        stmt = select(Document).where(Document.file_hash == file_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_chunks(self, document_id: UUID) -> Optional[Document]:
        """
        WHAT: Fetch document with eagerly loaded chunks.
        WHY: Avoids N+1 query when accessing chunks. Required for async SQLAlchemy.
        """
        stmt = (
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.id == document_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_with_stats(
        self, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Document]:
        """
        WHAT: Fetch documents ordered by creation date.
        WHY: Used for the document list UI with pagination.
        """
        stmt = (
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
