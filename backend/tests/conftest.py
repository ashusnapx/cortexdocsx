"""
WHAT: Pytest configuration and shared fixtures for CortexDocs ∞ test suite.
WHY: Centralizes test infrastructure — async session factory, mock services,
     and test configuration overrides. Enables isolated, repeatable tests.
WHEN: Loaded automatically by pytest before test execution.
WHERE: backend/tests/conftest.py
HOW: Async fixtures using pytest-asyncio with in-memory SQLite for speed.
ALTERNATIVES CONSIDERED:
  - Test against real PostgreSQL: Slower, requires Docker in CI.
  - Factory Boy: More boilerplate than simple fixtures for this test size.
TRADEOFFS:
  - SQLite differs from PostgreSQL in edge cases (JSONB, UUID) — acceptable for unit tests.
  - In-memory DB resets per test — intentional for isolation.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.domain.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///",
        ENVIRONMENT="test",
        LOG_LEVEL="DEBUG",
        LLM_PROVIDER="mock",
        RATE_LIMIT_ENABLED=False,
        FAISS_INDEX_DIR="./test_data/faiss",
        BM25_INDEX_DIR="./test_data/bm25",
        UPLOAD_DIR="./test_data/uploads",
    )


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async session with in-memory SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def mock_llm_provider() -> MagicMock:
    """Create a mock LLM provider for testing."""
    provider = MagicMock()
    provider.generate = AsyncMock(
        return_value="This is a mock LLM response for testing purposes."
    )
    provider.generate_stream = AsyncMock()
    provider.health_check = AsyncMock(
        return_value={"provider": "mock", "status": "ok"}
    )
    provider.circuit_breaker = MagicMock()
    provider.circuit_breaker.state = "closed"
    provider.circuit_breaker.failure_count = 0
    provider.circuit_breaker.get_status.return_value = {
        "state": "closed",
        "failure_count": 0,
    }
    return provider


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Create a mock vector store for testing."""
    store = MagicMock()
    store.is_loaded = True
    store.total_vectors = 100
    store.search = AsyncMock(return_value=([0, 1, 2], [0.9, 0.8, 0.7]))
    store.add_vectors = AsyncMock(return_value=[0, 1, 2])
    store.persist = AsyncMock()
    store.health_check = AsyncMock(
        return_value={"status": "ok", "total_vectors": 100}
    )
    return store


@pytest.fixture
def mock_bm25_store() -> MagicMock:
    """Create a mock BM25 store for testing."""
    store = MagicMock()
    store.is_loaded = True
    store.search = AsyncMock(return_value=([0, 1, 2], [5.0, 3.0, 1.0]))
    store.rebuild = AsyncMock()
    store.persist = AsyncMock()
    store.health_check = AsyncMock(
        return_value={"status": "ok", "total_documents": 50}
    )
    return store


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Create a mock embedding service for testing."""
    import numpy as np

    service = MagicMock()
    service.model_name = "test-model"
    service.dimension = 384
    service.is_loaded = True
    service.embed_texts = AsyncMock(
        return_value=np.random.rand(3, 384).astype(np.float32)
    )
    service.embed_query = AsyncMock(
        return_value=np.random.rand(384).astype(np.float32)
    )
    service.initialize = AsyncMock()
    service.health_check = AsyncMock(
        return_value={"status": "ok", "model": "test-model"}
    )
    return service


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Create a minimal valid PDF for testing."""
    # Minimal valid PDF (1 page, contains "Hello World")
    return (
        b"%PDF-1.0\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources"
        b"<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length 44>>\nstream\n"
        b"BT /F1 24 Tf 100 700 Td (Hello World) Tj ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000340 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n434\n%%EOF"
    )
