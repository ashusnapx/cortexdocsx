"""
WHAT: Abstract base repository defining the repository pattern interface.
WHY: Enforces consistent CRUD operations across all repositories.
     Enables dependency injection and testability — services depend on
     abstractions, not concrete implementations.
WHEN: Extended by all concrete repository classes.
WHERE: backend/app/repositories/base.py
HOW: Generic abstract class parameterized by SQLAlchemy model type.
ALTERNATIVES CONSIDERED:
  - No base class: Each repo reimplements CRUD — duplication.
  - Active Record pattern: Mixes domain logic with persistence — rejected.
TRADEOFFS:
  - Generic base adds slight complexity but eliminates ~80% of boilerplate per repo.
  - Abstract methods enforce interface but can't enforce transaction boundaries.
"""

import uuid
from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    WHAT: Generic async repository with CRUD operations.
    WHY: Single implementation of common DB patterns, reducing duplication.
    """

    def __init__(self, session: AsyncSession, model_class: Type[ModelT]) -> None:
        self._session = session
        self._model_class = model_class

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[ModelT]:
        """
        WHAT: Fetch a single record by primary key.
        WHY: Most common query pattern. Returns None if not found.
        """
        return await self._session.get(self._model_class, record_id)

    async def get_all(
        self, *, offset: int = 0, limit: int = 100
    ) -> Sequence[ModelT]:
        """
        WHAT: Fetch all records with pagination.
        WHY: Prevents unbounded result sets from exhausting memory.
        """
        stmt = (
            select(self._model_class)
            .offset(offset)
            .limit(limit)
            .order_by(self._model_class.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        """
        WHAT: Count total records in the table.
        WHY: Used for pagination metadata.
        """
        stmt = select(func.count()).select_from(self._model_class)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, instance: ModelT) -> ModelT:
        """
        WHAT: Insert a new record.
        WHY: Standardized creation with session management.
        """
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, instance: ModelT) -> ModelT:
        """
        WHAT: Update an existing record.
        WHY: Merges changes into the session for commit.
        """
        merged = await self._session.merge(instance)
        await self._session.flush()
        return merged

    async def delete_by_id(self, record_id: uuid.UUID) -> bool:
        """
        WHAT: Delete a record by primary key.
        WHY: Returns bool indicating whether a record was actually deleted.
        """
        instance = await self.get_by_id(record_id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True
