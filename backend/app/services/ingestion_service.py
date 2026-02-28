"""
WHAT: Ingestion orchestrator service — manages the full document upload pipeline.
WHY: Orchestrates parsing → chunking → embedding → indexing → DB write as a single
     cohesive pipeline with per-stage timing, error handling, and status tracking.
WHEN: Called as a background task after file upload API receives a valid PDF.
WHERE: backend/app/services/ingestion_service.py
HOW: Coordinates repositories, embedding service, vector store, and BM25 store.
     Reports per-stage latency for the transparency UI.
ALTERNATIVES CONSIDERED:
  - Celery task queue: Adds Redis/RabbitMQ dependency, overkill for local deployment.
  - Dramatiq: Similar to Celery, lighter but still an extra dependency.
  - Synchronous processing: Blocks the API response — unacceptable for large files.
TRADEOFFS:
  - Background tasks are in-process — no task persistence across restarts.
  - No distributed task queue — single-instance limitation, acceptable for local dev.
  - Full rebuild of BM25 index on each ingestion — O(n) but fast for <100k chunks.
"""

import hashlib
import io
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import (
    ErrorCode,
    IngestionStatus,
    PDF_MAGIC_BYTES,
    PDF_MAGIC_BYTES_LENGTH,
    PDF_MAGIC_BYTES_OFFSET,
)
from app.core.features import get_feature_flags
from app.domain.models import Chunk, Document, IngestionJob
from app.infrastructure.bm25_store import BM25StoreManager
from app.infrastructure.vector_store import VectorStoreManager
from app.observability.timing import PipelineTimer, timed_stage
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.ingestion_repo import IngestionRepository
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)


class IngestionService:
    """
    WHAT: Orchestrates the full document ingestion pipeline.
    WHY: Single entry point for the upload flow with full observability.
    """

    def __init__(
        self,
        session: AsyncSession,
        vector_store: VectorStoreManager,
        bm25_store: BM25StoreManager,
        embedding_service: EmbeddingService,
    ) -> None:
        self._session = session
        self._vector_store = vector_store
        self._bm25_store = bm25_store
        self._embedding_service = embedding_service
        self._settings = get_settings()
        self._chunking_service = ChunkingService()
        self._doc_repo = DocumentRepository(session)
        self._chunk_repo = ChunkRepository(session)
        self._ingestion_repo = IngestionRepository(session)

    async def ingest_document(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
    ) -> tuple[Document, IngestionJob, PipelineTimer]:
        """
        WHAT: Execute the full ingestion pipeline for a PDF document.
        WHY: Main entry point — validates, parses, chunks, embeds, indexes, persists.
        Returns: (Document, IngestionJob, PipelineTimer) for API response.
        """
        timer = PipelineTimer()
        timer.start()

        # Validate file
        self._validate_file(file_content, filename, mime_type)

        # Create document record
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Check for duplicate
        existing = await self._doc_repo.get_by_file_hash(file_hash)
        if existing:
            logger.info("duplicate_document_detected", file_hash=file_hash[:12])
            # Return existing document with its latest job
            jobs = await self._ingestion_repo.get_by_document_id(existing.id)
            latest_job = jobs[0] if jobs else None
            return existing, latest_job, timer

        document = Document(
            filename=filename,
            original_filename=filename,
            file_size_bytes=len(file_content),
            mime_type=mime_type,
            file_hash=file_hash,
        )
        document = await self._doc_repo.create(document)

        # Create ingestion job
        job = IngestionJob(
            document_id=document.id,
            status=IngestionStatus.PENDING.value,
            started_at=datetime.now(timezone.utc),
        )
        job = await self._ingestion_repo.create(job)
        await self._session.commit()

        try:
            # Stage 1: Parse PDF
            async with timed_stage(timer, "parsing") as ctx:
                job.status = IngestionStatus.PARSING.value
                await self._ingestion_repo.update(job)
                await self._session.commit()

                pages = self._parse_pdf(file_content)
                ctx["page_count"] = len(pages)
                job.page_count = len(pages)
                document.page_count = len(pages)

            job.parse_time_ms = timer.stages[-1].duration_ms

            # Stage 2: Chunk
            async with timed_stage(timer, "chunking") as ctx:
                job.status = IngestionStatus.CHUNKING.value
                await self._ingestion_repo.update(job)
                await self._session.commit()

                chunk_results = self._chunking_service.chunk_pages(pages)
                ctx["chunk_count"] = len(chunk_results)
                job.chunk_count = len(chunk_results)
                document.chunk_count = len(chunk_results)

            job.chunk_time_ms = timer.stages[-1].duration_ms

            # Stage 3: Embed
            async with timed_stage(timer, "embedding") as ctx:
                job.status = IngestionStatus.EMBEDDING.value
                await self._ingestion_repo.update(job)
                await self._session.commit()

                texts = [cr.content for cr in chunk_results]
                embeddings = await self._embedding_service.embed_texts(texts)
                ctx["embedding_count"] = len(embeddings)

            job.embed_time_ms = timer.stages[-1].duration_ms

            # Stage 4: Index
            async with timed_stage(timer, "indexing") as ctx:
                job.status = IngestionStatus.INDEXING.value
                await self._ingestion_repo.update(job)
                await self._session.commit()

                vector_ids = await self._vector_store.add_vectors(embeddings)
                await self._vector_store.persist()
                ctx["vector_ids_count"] = len(vector_ids)

            job.index_time_ms = timer.stages[-1].duration_ms

            # Stage 5: DB write
            async with timed_stage(timer, "db_write") as ctx:
                chunks = []
                for i, cr in enumerate(chunk_results):
                    chunk = Chunk(
                        document_id=document.id,
                        content=cr.content,
                        chunk_index=cr.chunk_index,
                        page_number=cr.page_number,
                        start_char=cr.start_char,
                        end_char=cr.end_char,
                        token_count=cr.token_count,
                        vector_store_id=vector_ids[i],
                        embedding_model=self._embedding_service.model_name,
                        chunk_metadata=cr.metadata,
                    )
                    chunks.append(chunk)

                await self._chunk_repo.bulk_create(chunks)
                await self._doc_repo.update(document)
                ctx["chunks_written"] = len(chunks)

            job.db_write_time_ms = timer.stages[-1].duration_ms

            # Rebuild BM25 index (includes all chunks)
            all_chunks = await self._chunk_repo.get_all_for_indexing()
            all_texts = [c.content for c in all_chunks]
            all_vector_ids = [c.vector_store_id for c in all_chunks]
            await self._bm25_store.rebuild(all_texts, all_vector_ids)
            await self._bm25_store.persist()

            # Mark complete
            job.status = IngestionStatus.COMPLETED.value
            job.completed_at = datetime.now(timezone.utc)
            job.total_time_ms = timer.total_ms
            await self._ingestion_repo.update(job)
            await self._session.commit()

            logger.info(
                "ingestion_completed",
                document_id=str(document.id),
                total_time_ms=round(timer.total_ms, 2),
                chunks=len(chunk_results),
                pages=len(pages),
            )

            return document, job, timer

        except Exception as e:
            job.status = IngestionStatus.FAILED.value
            job.error_message = str(e)
            job.error_code = ErrorCode.INGESTION_FAILED.value
            job.completed_at = datetime.now(timezone.utc)
            job.total_time_ms = timer.total_ms
            await self._ingestion_repo.update(job)
            await self._session.commit()

            logger.exception(
                "ingestion_failed",
                document_id=str(document.id),
                error=str(e),
            )
            raise

    def _validate_file(
        self, content: bytes, filename: str, mime_type: str
    ) -> None:
        """
        WHAT: Validate uploaded file before processing.
        WHY: Fail fast on invalid files — prevents wasting compute on bad input.
        Checks: size, MIME type, magic bytes (file signature).
        """
        settings = self._settings
        flags = get_feature_flags()

        # Size check
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(
                f"File size ({len(content)} bytes) exceeds limit ({max_bytes} bytes). "
                f"[{ErrorCode.FILE_TOO_LARGE.value}]"
            )

        # MIME type check
        if mime_type not in settings.ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Invalid MIME type: {mime_type}. Allowed: {settings.ALLOWED_MIME_TYPES}. "
                f"[{ErrorCode.INVALID_MIME_TYPE.value}]"
            )

        # Magic bytes validation (file signature)
        if flags.ENABLE_MAGIC_BYTES_VALIDATION:
            if len(content) < PDF_MAGIC_BYTES_LENGTH:
                raise ValueError(
                    f"File too small to be a valid PDF. [{ErrorCode.CORRUPT_FILE.value}]"
                )
            header = content[PDF_MAGIC_BYTES_OFFSET:PDF_MAGIC_BYTES_LENGTH]
            if not header.startswith(PDF_MAGIC_BYTES):
                raise ValueError(
                    f"File signature does not match PDF format. [{ErrorCode.CORRUPT_FILE.value}]"
                )

    def _parse_pdf(self, content: bytes) -> list[dict]:
        """
        WHAT: Extract text content from PDF, page by page.
        WHY: Page-level extraction preserves page numbers for citation accuracy.
        HOW: PyMuPDF (fitz) for robust PDF parsing with page metadata.
        """
        import fitz  # PyMuPDF

        pages: list[dict] = []
        try:
            doc = fitz.open(stream=content, filetype="pdf")

            max_pages = self._settings.MAX_PAGES_PER_DOCUMENT
            page_count = min(len(doc), max_pages)

            for page_num in range(page_count):
                page = doc[page_num]
                text = page.get_text("text")
                if text.strip():
                    pages.append({
                        "page_number": page_num + 1,
                        "text": text.strip(),
                    })

            doc.close()

        except Exception as e:
            raise ValueError(
                f"Failed to parse PDF: {str(e)}. [{ErrorCode.CORRUPT_FILE.value}]"
            )

        if not pages:
            raise ValueError(
                f"PDF contains no extractable text. [{ErrorCode.CORRUPT_FILE.value}]"
            )

        return pages
