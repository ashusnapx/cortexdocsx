"""
WHAT: FastAPI application factory with lifespan management.
WHY: Single entry point for the CortexDocs ∞ backend. Initializes all subsystems
     (DB, vector store, BM25, embedding model, LLM provider) during startup and
     performs graceful shutdown.
WHEN: Loaded by uvicorn as the ASGI application.
WHERE: backend/app/main.py
HOW: App factory pattern with contextmanager lifespan for resource management.
ALTERNATIVES CONSIDERED:
  - Django: Not async-native, heavier ORM assumptions.
  - Litestar: Newer, less ecosystem support than FastAPI.
  - Flask + async: Not natively async.
TRADEOFFS:
  - FastAPI's dependency injection is request-scoped — singletons need manual management.
  - Lifespan events run once — no per-worker initialization (fine for single-worker local dev).
"""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.dependencies import init_singletons
from app.domain.models import Base
from app.infrastructure.bm25_store import BM25StoreManager
from app.infrastructure.database import close_database, get_engine, init_database
from app.infrastructure.llm_provider import create_llm_provider
from app.infrastructure.vector_store import VectorStoreManager
from app.middleware.error_handler import register_error_handlers
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.observability.logging import configure_logging
from app.services.embedding_service import EmbeddingService
from app.services.reranking_service import RerankingService

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    WHAT: Application lifespan manager — startup and shutdown hooks.
    WHY: Initialize all subsystems before serving requests, clean up after.
    """
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────
    configure_logging()
    logger.info("cortexdocs_starting", version=settings.APP_VERSION)

    # Create data directories
    for dir_path in [settings.UPLOAD_DIR, settings.FAISS_INDEX_DIR, settings.BM25_INDEX_DIR]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    # Initialize database
    await init_database()

    # Create tables (development convenience — use Alembic in production)
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")

    # Initialize infrastructure singletons
    vector_store = VectorStoreManager()
    await vector_store.initialize()

    bm25_store = BM25StoreManager()
    await bm25_store.initialize()

    embedding_service = EmbeddingService()
    reranking_service = RerankingService()
    llm_provider = create_llm_provider()

    init_singletons(
        vector_store=vector_store,
        bm25_store=bm25_store,
        embedding_service=embedding_service,
        reranking_service=reranking_service,
        llm_provider=llm_provider,
    )

    logger.info("cortexdocs_started", environment=settings.ENVIRONMENT)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    logger.info("cortexdocs_shutting_down")
    await close_database()
    logger.info("cortexdocs_stopped")


def create_app() -> FastAPI:
    """
    WHAT: FastAPI application factory.
    WHY: Clean instantiation with all middleware, routes, and error handlers.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production-grade multi-document AI retrieval engine",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Middleware (order matters: outermost first) ──────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ── Error handlers ──────────────────────────────────────────────
    register_error_handlers(app)

    # ── Routes ──────────────────────────────────────────────────────
    app.include_router(api_v1_router)

    return app


# ASGI entry point
app = create_app()
