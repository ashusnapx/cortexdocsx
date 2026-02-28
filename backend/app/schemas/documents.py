"""
WHAT: Pydantic schemas for document upload and ingestion API endpoints.
WHY: Request validation and response serialization for the upload pipeline.
     Ensures type-safe data exchange between frontend and backend.
WHEN: Used by document API routes for request parsing and response formatting.
WHERE: backend/app/schemas/documents.py
HOW: Pydantic v2 models with field validation and serialization aliases.
ALTERNATIVES CONSIDERED: N/A — Pydantic is the standard for FastAPI schemas.
TRADEOFFS: Schema duplication vs ORM models — intentional separation of concerns.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PipelineTiming


class DocumentResponse(BaseModel):
    """Response schema for a single document."""
    id: UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    page_count: int
    chunk_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Response schema for listing documents."""
    documents: list[DocumentResponse]
    total: int


class IngestionJobResponse(BaseModel):
    """Response schema for an ingestion job with per-stage timing."""
    id: UUID
    document_id: UUID
    status: str
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_count: int = 0

    # Per-stage latency
    parse_time_ms: Optional[float] = None
    chunk_time_ms: Optional[float] = None
    embed_time_ms: Optional[float] = None
    index_time_ms: Optional[float] = None
    db_write_time_ms: Optional[float] = None
    total_time_ms: Optional[float] = None

    # Pipeline stats
    chunk_count: int = 0
    page_count: int = 0
    pipeline_metadata: dict = Field(default_factory=dict)

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    """Response schema for a document upload request."""
    document: DocumentResponse
    ingestion_job: IngestionJobResponse
    timing: Optional[PipelineTiming] = None


class IngestionStatusResponse(BaseModel):
    """Response for checking ingestion status."""
    job: IngestionJobResponse
    document: DocumentResponse
