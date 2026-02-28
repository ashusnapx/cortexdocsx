"""
WHAT: Ingestion job repository for pipeline tracking operations.
WHY: Tracks the lifecycle of document ingestion jobs. Enables the UI to show
     real-time pipeline progress and error details.
WHEN: Used by IngestionService to create, update, and query job status.
WHERE: backend/app/repositories/ingestion_repo.py
HOW: Extends BaseRepository with status-based queries.
ALTERNATIVES CONSIDERED: N/A — repository pattern.
TRADEOFFS: Job records persist indefinitely — add cleanup policy if storage becomes a concern.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import IngestionJob
from app.repositories.base import BaseRepository


class IngestionRepository(BaseRepository[IngestionJob]):
    """
    WHAT: Repository for ingestion job lifecycle management.
    WHY: Separates job persistence from orchestration logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, IngestionJob)

    async def get_by_document_id(
        self, document_id: UUID
    ) -> Sequence[IngestionJob]:
        """
        WHAT: Fetch all ingestion jobs for a specific document.
        WHY: Shows upload history including retries and failures.
        """
        stmt = (
            select(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_latest_by_document_id(
        self, document_id: UUID
    ) -> Optional[IngestionJob]:
        """
        WHAT: Get the most recent ingestion job for a document.
        WHY: Used to check current processing status.
        """
        stmt = (
            select(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_jobs(self) -> Sequence[IngestionJob]:
        """
        WHAT: Fetch all jobs in pending/processing state.
        WHY: Used for health check and recovery on restart.
        """
        stmt = (
            select(IngestionJob)
            .where(IngestionJob.status.in_(["pending", "parsing", "chunking", "embedding", "indexing"]))
            .order_by(IngestionJob.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
