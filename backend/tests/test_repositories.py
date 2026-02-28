"""
WHAT: Repository layer unit tests.
WHY: Validates CRUD operations, deduplication, and batch operations
     against an in-memory SQLite database.
WHEN: Run via pytest as part of the test suite.
WHERE: backend/tests/test_repositories.py
HOW: Uses async fixtures from conftest.py for isolated test sessions.
ALTERNATIVES CONSIDERED: Integration tests against PostgreSQL — reserved for CI.
TRADEOFFS: SQLite in-memory is fast but doesn't test PostgreSQL-specific features.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Chunk, Document, IngestionJob, QueryLog
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.ingestion_repo import IngestionRepository
from app.repositories.query_log_repo import QueryLogRepository


@pytest.mark.asyncio
class TestDocumentRepository:
    """Tests for DocumentRepository CRUD and queries."""

    async def test_create_and_get_document(self, async_session: AsyncSession):
        repo = DocumentRepository(async_session)

        doc = Document(
            filename="test.pdf",
            original_filename="test.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            file_hash="abc123hash",
        )

        created = await repo.create(doc)
        assert created.id is not None
        assert created.filename == "test.pdf"

        retrieved = await repo.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.filename == "test.pdf"

    async def test_get_by_file_hash(self, async_session: AsyncSession):
        repo = DocumentRepository(async_session)

        doc = Document(
            filename="unique.pdf",
            original_filename="unique.pdf",
            file_size_bytes=2048,
            mime_type="application/pdf",
            file_hash="uniquehash123",
        )
        await repo.create(doc)

        found = await repo.get_by_file_hash("uniquehash123")
        assert found is not None
        assert found.filename == "unique.pdf"

        not_found = await repo.get_by_file_hash("nonexistent")
        assert not_found is None

    async def test_count(self, async_session: AsyncSession):
        repo = DocumentRepository(async_session)

        for i in range(3):
            doc = Document(
                filename=f"doc{i}.pdf",
                original_filename=f"doc{i}.pdf",
                file_size_bytes=1024,
                mime_type="application/pdf",
                file_hash=f"hash{i}",
            )
            await repo.create(doc)

        count = await repo.count()
        assert count == 3

    async def test_delete(self, async_session: AsyncSession):
        repo = DocumentRepository(async_session)

        doc = Document(
            filename="delete_me.pdf",
            original_filename="delete_me.pdf",
            file_size_bytes=512,
            mime_type="application/pdf",
            file_hash="deletehash",
        )
        created = await repo.create(doc)

        deleted = await repo.delete_by_id(created.id)
        assert deleted is True

        retrieved = await repo.get_by_id(created.id)
        assert retrieved is None


@pytest.mark.asyncio
class TestChunkRepository:
    """Tests for ChunkRepository batch operations."""

    async def test_bulk_create(self, async_session: AsyncSession):
        doc_repo = DocumentRepository(async_session)
        chunk_repo = ChunkRepository(async_session)

        doc = Document(
            filename="chunked.pdf",
            original_filename="chunked.pdf",
            file_size_bytes=4096,
            mime_type="application/pdf",
            file_hash="chunkedhash",
        )
        doc = await doc_repo.create(doc)

        chunks = [
            Chunk(
                document_id=doc.id,
                content=f"Chunk content {i}",
                chunk_index=i,
                page_number=1,
                embedding_model="test-model",
                vector_store_id=i,
            )
            for i in range(5)
        ]

        created = await chunk_repo.bulk_create(chunks)
        assert len(created) == 5

        by_doc = await chunk_repo.get_by_document_id(doc.id)
        assert len(by_doc) == 5


@pytest.mark.asyncio
class TestQueryLogRepository:
    """Tests for QueryLogRepository."""

    async def test_create_and_retrieve(self, async_session: AsyncSession):
        repo = QueryLogRepository(async_session)

        log = QueryLog(
            query_text="What is machine learning?",
            intent="precise",
            response_text="Machine learning is...",
            confidence_score=0.85,
            request_id="test-req-123",
        )
        created = await repo.create(log)
        assert created.id is not None

        retrieved = await repo.get_by_request_id("test-req-123")
        assert retrieved is not None
        assert retrieved.query_text == "What is machine learning?"

    async def test_get_recent(self, async_session: AsyncSession):
        repo = QueryLogRepository(async_session)

        for i in range(5):
            log = QueryLog(
                query_text=f"Query {i}",
                intent="precise",
                request_id=f"req-{i}",
            )
            await repo.create(log)

        recent = await repo.get_recent(limit=3)
        assert len(recent) == 3
