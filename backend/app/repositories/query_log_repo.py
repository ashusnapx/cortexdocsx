"""
WHAT: Query log repository for query telemetry persistence.
WHY: Enables deterministic query replay, debugging, and evaluation harness.
     Every query execution is fully logged including intermediate scores,
     model versions, and feature flag state.
WHEN: Used by QueryService after each query execution.
WHERE: backend/app/repositories/query_log_repo.py
HOW: Extends BaseRepository with replay and analytics queries.
ALTERNATIVES CONSIDERED: N/A — repository pattern.
TRADEOFFS: Storing full telemetry per query grows storage — add TTL/archival if needed.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import QueryLog
from app.repositories.base import BaseRepository


class QueryLogRepository(BaseRepository[QueryLog]):
    """
    WHAT: Repository for query execution telemetry.
    WHY: Enables query replay, audit trails, and evaluation.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, QueryLog)

    async def get_by_request_id(self, request_id: str) -> Optional[QueryLog]:
        """
        WHAT: Fetch query log by request ID.
        WHY: Enables correlation between HTTP request and query execution.
        """
        stmt = select(QueryLog).where(QueryLog.request_id == request_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent(self, limit: int = 50) -> Sequence[QueryLog]:
        """
        WHAT: Fetch the most recent query logs.
        WHY: Used for the evaluation dashboard and debugging.
        """
        stmt = (
            select(QueryLog)
            .order_by(QueryLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_intent(
        self, intent: str, *, limit: int = 50
    ) -> Sequence[QueryLog]:
        """
        WHAT: Fetch query logs filtered by intent classification.
        WHY: Enables per-intent performance analysis.
        """
        stmt = (
            select(QueryLog)
            .where(QueryLog.intent == intent)
            .order_by(QueryLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
