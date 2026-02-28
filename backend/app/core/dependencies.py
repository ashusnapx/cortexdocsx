"""
WHAT: Dependency injection container for CortexDocs ∞.
WHY: Centralizes service instantiation and wiring. Enables clean DI for route handlers
     and testability via override. Services depend on abstractions, not concrete construction.
WHEN: Used by FastAPI's Depends() system for per-request dependency resolution.
WHERE: backend/app/core/dependencies.py
HOW: Factory functions that create service instances with their required dependencies.
ALTERNATIVES CONSIDERED:
  - dependency-injector library: Heavier, more boilerplate for simpler patterns.
  - Manual construction in routes: Tight coupling, hard to test.
  - Global singletons: No per-request isolation, testing difficulties.
TRADEOFFS:
  - Factory functions create new instances per request for stateful objects — intentional
    for session isolation. Singletons used only for stateless infrastructure (vector store, etc.).
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.bm25_store import BM25StoreManager
from app.infrastructure.database import get_session
from app.infrastructure.llm_provider import MockLLMProvider, OpenAICompatibleProvider
from app.infrastructure.vector_store import VectorStoreManager
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.ingestion_repo import IngestionRepository
from app.repositories.query_log_repo import QueryLogRepository
from app.services.confidence_service import ConfidenceService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.intent_service import IntentService
from app.services.query_service import QueryService
from app.services.reranking_service import RerankingService
from app.services.retrieval_service import RetrievalService

# ─── Singleton Infrastructure (created once, shared across requests) ──

_vector_store: VectorStoreManager | None = None
_bm25_store: BM25StoreManager | None = None
_embedding_service: EmbeddingService | None = None
_reranking_service: RerankingService | None = None
_llm_provider: MockLLMProvider | OpenAICompatibleProvider | None = None
_intent_service: IntentService | None = None
_confidence_service: ConfidenceService | None = None


def get_vector_store() -> VectorStoreManager:
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized")
    return _vector_store


def get_bm25_store() -> BM25StoreManager:
    if _bm25_store is None:
        raise RuntimeError("BM25 store not initialized")
    return _bm25_store


def get_embedding_service() -> EmbeddingService:
    if _embedding_service is None:
        raise RuntimeError("Embedding service not initialized")
    return _embedding_service


def get_reranking_service() -> RerankingService:
    if _reranking_service is None:
        raise RuntimeError("Reranking service not initialized")
    return _reranking_service


def get_llm_provider() -> MockLLMProvider | OpenAICompatibleProvider:
    if _llm_provider is None:
        raise RuntimeError("LLM provider not initialized")
    return _llm_provider


def get_intent_service() -> IntentService:
    if _intent_service is None:
        raise RuntimeError("Intent service not initialized")
    return _intent_service


def get_confidence_service() -> ConfidenceService:
    if _confidence_service is None:
        raise RuntimeError("Confidence service not initialized")
    return _confidence_service


def init_singletons(
    vector_store: VectorStoreManager,
    bm25_store: BM25StoreManager,
    embedding_service: EmbeddingService,
    reranking_service: RerankingService,
    llm_provider: MockLLMProvider | OpenAICompatibleProvider,
) -> None:
    """Initialize all singleton infrastructure services."""
    global _vector_store, _bm25_store, _embedding_service
    global _reranking_service, _llm_provider, _intent_service, _confidence_service

    _vector_store = vector_store
    _bm25_store = bm25_store
    _embedding_service = embedding_service
    _reranking_service = reranking_service
    _llm_provider = llm_provider
    _intent_service = IntentService()
    _confidence_service = ConfidenceService()


# ─── Per-Request Service Factories ─────────────────────────────────


async def get_ingestion_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IngestionService:
    return IngestionService(
        session=session,
        vector_store=get_vector_store(),
        bm25_store=get_bm25_store(),
        embedding_service=get_embedding_service(),
    )


async def get_retrieval_service() -> RetrievalService:
    return RetrievalService(
        vector_store=get_vector_store(),
        bm25_store=get_bm25_store(),
        embedding_service=get_embedding_service(),
    )


async def get_query_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> QueryService:
    return QueryService(
        session=session,
        retrieval_service=RetrievalService(
            vector_store=get_vector_store(),
            bm25_store=get_bm25_store(),
            embedding_service=get_embedding_service(),
        ),
        reranking_service=get_reranking_service(),
        confidence_service=get_confidence_service(),
        intent_service=get_intent_service(),
        llm_provider=get_llm_provider(),
        chunk_repo=ChunkRepository(session),
        query_log_repo=QueryLogRepository(session),
    )
