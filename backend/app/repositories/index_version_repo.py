"""
WHAT: Index version repository for vector/BM25 index snapshot management.
WHY: Enables index versioning, rollback to previous versions, and drift detection.
     Production systems need reproducibility — this table tracks which index version
     is active and what parameters were used to build it.
WHEN: Used during index rebuilds, rollbacks, and health checks.
WHERE: backend/app/repositories/index_version_repo.py
HOW: Extends BaseRepository with version-specific queries.
ALTERNATIVES CONSIDERED: File-based versioning — rejected for lack of queryability.
TRADEOFFS: Adds DB overhead per index operation — minimal and worth the auditability.
"""

from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import IndexVersion
from app.repositories.base import BaseRepository


class IndexVersionRepository(BaseRepository[IndexVersion]):
    """
    WHAT: Repository for index version lifecycle management.
    WHY: Tracks index builds, enables rollback, detects drift.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, IndexVersion)

    async def get_active_version(self, index_type: str) -> Optional[IndexVersion]:
        """
        WHAT: Get the currently active index version for a given type.
        WHY: Used at query time to know which index file to load.
        """
        stmt = (
            select(IndexVersion)
            .where(
                IndexVersion.index_type == index_type,
                IndexVersion.is_active == True,
            )
            .order_by(IndexVersion.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_version_number(self, index_type: str) -> int:
        """
        WHAT: Get the highest version number for an index type.
        WHY: Used to assign the next version number during index rebuild.
        """
        stmt = (
            select(IndexVersion.version)
            .where(IndexVersion.index_type == index_type)
            .order_by(IndexVersion.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        version = result.scalar_one_or_none()
        return version if version is not None else 0

    async def deactivate_all(self, index_type: str) -> None:
        """
        WHAT: Deactivate all versions of a given index type.
        WHY: Called before activating a new version to ensure single active version.
        """
        stmt = (
            update(IndexVersion)
            .where(IndexVersion.index_type == index_type)
            .values(is_active=False)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_version_history(
        self, index_type: str, *, limit: int = 10
    ) -> Sequence[IndexVersion]:
        """
        WHAT: Fetch version history for an index type.
        WHY: Used for rollback UI and audit trail.
        """
        stmt = (
            select(IndexVersion)
            .where(IndexVersion.index_type == index_type)
            .order_by(IndexVersion.version.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
