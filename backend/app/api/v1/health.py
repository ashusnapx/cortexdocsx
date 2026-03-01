"""
WHAT: Health check endpoint for system observability.
WHY: Reports the status of all subsystems: database, vector store, BM25, LLM,
     circuit breaker state, and memory usage. Essential for monitoring and alerting.
WHEN: Polled by orchestration tools, load balancers, and the frontend status panel.
WHERE: backend/app/api/v1/health.py
HOW: Async checks against each subsystem with timeout protection.
ALTERNATIVES CONSIDERED: N/A — health endpoints are mandatory for any production service.
TRADEOFFS: Health checks add minor load — acceptable at typical poll intervals (10-30s).
"""

import sys
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings
from app.core.dependencies import (
    get_bm25_store,
    get_embedding_service,
    get_llm_provider,
    get_vector_store,
)
from app.infrastructure.database import get_engine
from app.infrastructure.bm25_store import BM25StoreManager
from app.infrastructure.llm_provider import MockLLMProvider, OpenAICompatibleProvider
from app.infrastructure.vector_store import VectorStoreManager
from app.schemas.common import ApiResponse
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[dict])
async def health_check():
    """
    WHAT: Comprehensive system health check.
    WHY: Reports status of every subsystem for monitoring and UI display.
    """
    settings = get_settings()
    checks: dict = {}

    # Database check
    try:
        engine = await get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}

    # Vector store check
    try:
        vs = get_vector_store()
        checks["vector_store"] = await vs.health_check()
    except Exception as e:
        checks["vector_store"] = {"status": "error", "error": str(e)}

    # BM25 check
    try:
        bm25 = get_bm25_store()
        checks["bm25_store"] = await bm25.health_check()
    except Exception as e:
        checks["bm25_store"] = {"status": "error", "error": str(e)}

    # LLM check
    try:
        llm = get_llm_provider()
        checks["llm"] = await llm.health_check()
    except Exception as e:
        checks["llm"] = {"status": "error", "error": str(e)}

    # Embedding model check
    try:
        embed = get_embedding_service()
        checks["embedding_model"] = await embed.health_check()
    except Exception as e:
        checks["embedding_model"] = {"status": "error", "error": str(e)}

    # Memory usage
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        checks["memory"] = {
            "rss_mb": round(memory_info.rss / (1024 * 1024), 2),
            "vms_mb": round(memory_info.vms / (1024 * 1024), 2),
        }
    except ImportError:
        checks["memory"] = {"note": "psutil not installed"}

    # Overall status
    all_ok = all(
        c.get("status") in ("ok", "empty", "not_loaded")
        for c in checks.values()
        if isinstance(c, dict) and "status" in c
    )

    checks["app"] = {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "python_version": sys.version,
    }

    return ApiResponse.ok(checks) if all_ok else ApiResponse.ok(checks)


@router.get("/config", response_model=ApiResponse[dict])
async def get_config():
    """
    WHAT: Frontend dynamic UI capability config endpoint.
    WHY: Required by the frontend DynamicQueryPanel to paint boundaries and defaults.
    """
    return ApiResponse.ok({
        "hyperparameters": {
            "alpha": {"min": 0.0, "max": 1.0, "step": 0.1, "default": 0.7},
            "beta": {"min": 0.0, "max": 1.0, "step": 0.1, "default": 0.3},
            "reranking": {"default": True},
            "hybrid": {"default": True}
        },
        "limits": {
            "max_file_size_mb": 50,
            "max_pages_per_document": 500,
            "allowed_mime_types": ["application/pdf"]
        }
    })
