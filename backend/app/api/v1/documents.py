"""
WHAT: Document upload and management API endpoints.
WHY: RESTful endpoints for PDF upload, ingestion status, and document listing.
     No business logic here — delegates to IngestionService.
WHEN: Called by the frontend upload panel.
WHERE: backend/app/api/v1/documents.py
HOW: FastAPI router with dependency injection, background task for ingestion.
ALTERNATIVES CONSIDERED: N/A — standard REST pattern.
TRADEOFFS: Background task means upload returns before ingestion completes — 
    client polls for status. Better UX than blocking a 30s+ upload request.
"""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_ingestion_service
from app.infrastructure.database import get_session
from app.repositories.document_repo import DocumentRepository
from app.repositories.ingestion_repo import IngestionRepository
from app.schemas.common import ApiResponse, PipelineTiming, TimingStage
from app.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    IngestionJobResponse,
    IngestionStatusResponse,
    UploadResponse,
)
from app.services.ingestion_service import IngestionService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=ApiResponse[UploadResponse])
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    """
    WHAT: Upload a PDF document for ingestion.
    WHY: Entry point for the upload pipeline.
    HOW: Reads file content, delegates to IngestionService, returns status.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "document_upload_started",
        filename=file.filename,
        content_type=file.content_type,
        request_id=request_id,
    )

    content = await file.read()

    try:
        document, job, timer = await ingestion_service.ingest_document(
            file_content=content,
            filename=file.filename or "unknown.pdf",
            mime_type=file.content_type or "application/pdf",
        )

        timing = PipelineTiming(
            stages=[
                TimingStage(
                    stage=s.stage,
                    duration_ms=s.duration_ms,
                    metadata=s.metadata,
                )
                for s in timer.stages
            ],
            total_ms=round(timer.total_ms, 2),
        )

        return ApiResponse.ok(
            UploadResponse(
                document=DocumentResponse.model_validate(document),
                ingestion_job=IngestionJobResponse.model_validate(job),
                timing=timing,
            )
        )

    except ValueError as e:
        return ApiResponse.fail(
            code="VALIDATION_ERROR",
            message=str(e),
            request_id=request_id,
        )
    except Exception as e:
        logger.exception("upload_failed", error=str(e))
        return ApiResponse.fail(
            code="INGESTION_FAILED",
            message=f"Ingestion failed: {str(e)}",
            request_id=request_id,
        )


@router.get("", response_model=ApiResponse[DocumentListResponse])
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    offset: int = 0,
    limit: int = 50,
):
    """
    WHAT: List all uploaded documents with pagination.
    WHY: Used by the frontend document list view.
    """
    repo = DocumentRepository(session)
    documents = await repo.get_all_with_stats(offset=offset, limit=limit)
    total = await repo.count()

    return ApiResponse.ok(
        DocumentListResponse(
            documents=[DocumentResponse.model_validate(d) for d in documents],
            total=total,
        )
    )


@router.get("/{document_id}", response_model=ApiResponse[DocumentResponse])
async def get_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """
    WHAT: Get a single document by ID.
    WHY: Used for document detail view.
    """
    repo = DocumentRepository(session)
    document = await repo.get_by_id(document_id)

    if document is None:
        return ApiResponse.fail(
            code="RECORD_NOT_FOUND",
            message=f"Document {document_id} not found",
        )

    return ApiResponse.ok(DocumentResponse.model_validate(document))


@router.get(
    "/{document_id}/ingestion",
    response_model=ApiResponse[IngestionStatusResponse],
)
async def get_ingestion_status(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """
    WHAT: Get the ingestion status for a document.
    WHY: Frontend polls this to show real-time pipeline progress.
    """
    doc_repo = DocumentRepository(session)
    ing_repo = IngestionRepository(session)

    document = await doc_repo.get_by_id(document_id)
    if document is None:
        return ApiResponse.fail(
            code="RECORD_NOT_FOUND",
            message=f"Document {document_id} not found",
        )

    job = await ing_repo.get_latest_by_document_id(document_id)
    if job is None:
        return ApiResponse.fail(
            code="RECORD_NOT_FOUND",
            message=f"No ingestion job found for document {document_id}",
        )

    return ApiResponse.ok(
        IngestionStatusResponse(
            job=IngestionJobResponse.model_validate(job),
            document=DocumentResponse.model_validate(document),
        )
    )
