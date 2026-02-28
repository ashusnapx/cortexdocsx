"""
WHAT: SQLAlchemy 2.0 ORM models for CortexDocs ∞ persistence layer.
WHY: Typed, declarative models with relationships, indexes, and constraints.
     Async-compatible via SQLAlchemy 2.0 mapped_column syntax.
WHEN: Used by repositories for all DB operations. Referenced by Alembic for migrations.
WHERE: backend/app/domain/models.py
HOW: DeclarativeBase with mapped_column, proper indexing on frequent query patterns.
ALTERNATIVES CONSIDERED:
  - Raw SQL: No type safety, migration headaches.
  - Tortoise ORM: Less mature async ecosystem than SQLAlchemy 2.0.
  - SQLModel: Tight Pydantic coupling causes serialization edge cases.
TRADEOFFS:
  - SQLAlchemy 2.0 async requires careful session management (no lazy loading).
  - mapped_column verbose but explicit — preferred for maintainability.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """
    WHAT: SQLAlchemy declarative base for all ORM models.
    WHY: Single inheritance root enables shared metadata and migration discovery.
    """
    pass


class Document(Base):
    """
    WHAT: Represents an uploaded PDF document.
    WHY: Tracks document metadata, upload status, and links to child chunks.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(
        "IngestionJob", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_documents_file_hash", "file_hash"),
        Index("idx_documents_created_at", "created_at"),
    )


class Chunk(Base):
    """
    WHAT: A text chunk derived from a document, with embedding metadata.
    WHY: Fundamental retrieval unit. Links text content to vector store positions.
    """

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_char: Mapped[int] = mapped_column(Integer, default=0)
    end_char: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    vector_store_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(256), nullable=False)
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_document_id", "document_id"),
        Index("idx_chunks_vector_store_id", "vector_store_id"),
        Index("idx_chunks_page_number", "page_number"),
    )


class IngestionJob(Base):
    """
    WHAT: Tracks the lifecycle of a document ingestion pipeline run.
    WHY: Enables pipeline observability, error tracking, and retry visibility.
    """

    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Per-stage latency tracking (milliseconds)
    parse_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    chunk_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    embed_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    index_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    db_write_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Pipeline metadata
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    pipeline_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="ingestion_jobs")

    __table_args__ = (
        Index("idx_ingestion_jobs_document_id", "document_id"),
        Index("idx_ingestion_jobs_status", "status"),
        Index("idx_ingestion_jobs_created_at", "created_at"),
    )


class QueryLog(Base):
    """
    WHAT: Full telemetry record for a query execution.
    WHY: Enables deterministic query replay, debugging, and evaluation.
         Stores every intermediate result for complete auditability.
    """

    __tablename__ = "query_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(32), nullable=False)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Retrieval telemetry
    retrieved_chunk_ids: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    vector_scores: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    bm25_scores: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    combined_scores: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    reranker_scores: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    final_chunk_ids: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    # Confidence breakdown
    confidence_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    contradictions_detected: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    # Performance telemetry
    intent_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retrieval_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rerank_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Model versions (for drift detection / replay)
    embedding_model_version: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    reranker_model_version: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    llm_model_version: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Feature flag state at query time (for replay accuracy)
    feature_flags_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # Request metadata
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_query_logs_created_at", "created_at"),
        Index("idx_query_logs_intent", "intent"),
        Index("idx_query_logs_request_id", "request_id"),
    )


class IndexVersion(Base):
    """
    WHAT: Tracks vector/BM25 index versions for snapshotting and rollback.
    WHY: Production systems need reproducibility. Enables rollback to previous
         index state if a bad batch is ingested.
    """

    __tablename__ = "index_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    index_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'faiss' or 'bm25'
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[str] = mapped_column(String(256), nullable=False)
    chunking_params: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    health_status: Mapped[str] = mapped_column(String(32), default="healthy")
    build_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_index_versions_type_active", "index_type", "is_active"),
        Index("idx_index_versions_version", "version"),
    )
