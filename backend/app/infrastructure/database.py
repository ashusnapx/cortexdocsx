"""
WHAT: Async database engine, session factory, and connection management.
WHY: Centralizes all DB connectivity. Async engine enables non-blocking I/O during
     concurrent PDF processing and query handling. Connection pooling prevents
     connection exhaustion under load.
WHEN: Initialized at application startup via lifespan. Sessions injected per-request.
WHERE: backend/app/infrastructure/database.py
HOW: SQLAlchemy 2.0 create_async_engine with pool configuration from Settings.
ALTERNATIVES CONSIDERED:
  - Sync SQLAlchemy: Blocks event loop during DB calls — unacceptable for async FastAPI.
  - Raw asyncpg: No ORM, manual SQL — maintenance burden.
  - Databases library: Less mature, fewer features than SQLAlchemy 2.0 async.
TRADEOFFS:
  - Async SQLAlchemy disables lazy loading — all relationships must be eagerly loaded.
  - Connection pool tuning is deployment-specific — defaults optimized for local dev.
"""

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database() -> None:
    """
    WHAT: Initialize the async database engine and session factory.
    WHY: Called once during app lifespan startup. Creates connection pool.
    HOW: Reads DB config from Settings, creates engine with pool params.
    """
    global _engine, _session_factory
    settings = get_settings()

    _engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        echo=settings.DB_ECHO,
        pool_pre_ping=True,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info(
        "database_initialized",
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )


async def close_database() -> None:
    """
    WHAT: Gracefully close the database engine and all connections.
    WHY: Called during app lifespan shutdown. Prevents connection leaks.
    """
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        logger.info("database_closed")
    _engine = None
    _session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    WHAT: Dependency injectable async session generator.
    WHY: Provides a session per-request with automatic cleanup.
    HOW: Yields a session from the factory, commits on success, rolls back on error.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_engine() -> AsyncEngine:
    """
    WHAT: Returns the active async engine for direct operations (health checks, raw SQL).
    WHY: Some operations (health pings) need engine-level access, not session-level.
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _engine
