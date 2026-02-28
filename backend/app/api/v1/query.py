"""
WHAT: Query API endpoints with SSE streaming support.
WHY: Handles user queries with full pipeline execution and streams responses.
     SSE (Server-Sent Events) chosen for simplicity — unidirectional server→client
     streaming without WebSocket connection upgrade overhead.
WHEN: Called by the frontend query panel.
WHERE: backend/app/api/v1/query.py
HOW: POST /query for full response, POST /query/stream for SSE streaming.
ALTERNATIVES CONSIDERED:
  - WebSockets: Bidirectional channel is unnecessary — queries are request/response.
  - Long polling: Higher latency, more complex client logic.
  - gRPC streaming: Not HTTP-native, harder for browser consumption.
TRADEOFFS:
  - SSE is HTTP/1.1+ only natively (works fine with HTTP/2).
  - No client→server streaming (not needed for query responses).
  - Easier browser debugging than WebSockets (standard HTTP).
"""

import json
from typing import Annotated, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_query_service, get_llm_provider
from app.infrastructure.database import get_session
from app.repositories.query_log_repo import QueryLogRepository
from app.schemas.common import ApiResponse
from app.schemas.query import QueryRequest, QueryResponse, QueryReplayResponse
from app.services.query_service import QueryService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=ApiResponse[QueryResponse])
async def execute_query(
    query_request: QueryRequest,
    request: Request,
    query_service: QueryService = Depends(get_query_service),
):
    """
    WHAT: Execute a query against the document corpus.
    WHY: Main query endpoint returning full response with transparency data.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    client_ip = request.client.host if request.client else "unknown"

    logger.info(
        "query_received",
        query_preview=query_request.query[:100],
        request_id=request_id,
    )

    try:
        response = await query_service.execute_query(
            query=query_request.query,
            request_id=request_id,
            client_ip=client_ip,
            top_k=query_request.top_k,
            alpha=query_request.alpha,
            beta=query_request.beta,
            enable_reranking=query_request.enable_reranking,
            enable_hybrid=query_request.enable_hybrid,
            intent_override=query_request.intent_override,
        )

        return ApiResponse.ok(response)

    except RuntimeError as e:
        if "Circuit breaker" in str(e):
            return ApiResponse.fail(
                code="LLM_CIRCUIT_OPEN",
                message="LLM service is temporarily unavailable. Please try again later.",
                request_id=request_id,
            )
        raise

    except Exception as e:
        logger.exception("query_failed", error=str(e))
        return ApiResponse.fail(
            code="RETRIEVAL_FAILED",
            message=f"Query execution failed: {str(e)}",
            request_id=request_id,
        )


@router.post("/stream")
async def stream_query(
    query_request: QueryRequest,
    request: Request,
    query_service: QueryService = Depends(get_query_service),
):
    """
    WHAT: Execute a query with SSE streaming response.
    WHY: Real-time token-by-token delivery for better UX.
    HOW: Runs pipeline, then streams LLM output via SSE events.
         Sends pipeline stages as events before the answer stream.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    async def event_generator():
        try:
            # Execute full pipeline (non-streaming part)
            response = await query_service.execute_query(
                query=query_request.query,
                request_id=request_id,
                client_ip=request.client.host if request.client else "unknown",
                top_k=query_request.top_k,
                alpha=query_request.alpha,
                beta=query_request.beta,
                enable_reranking=query_request.enable_reranking,
                enable_hybrid=query_request.enable_hybrid,
                intent_override=query_request.intent_override,
            )

            # Send pipeline stages
            for stage in response.timing.stages:
                event_data = json.dumps({
                    "stage": stage.stage,
                    "duration_ms": stage.duration_ms,
                    "metadata": stage.metadata,
                })
                yield f"event: stage\ndata: {event_data}\n\n"

            # Send metrics
            metrics_data = json.dumps({
                "intent": response.intent,
                "confidence": response.confidence.model_dump(),
                "retrieval_metrics": response.retrieval_metrics.model_dump(),
                "timing": response.timing.model_dump(),
                "contradictions": [c.model_dump() for c in response.contradictions],
                "model_versions": response.model_versions,
                "feature_flags": response.feature_flags,
            })
            yield f"event: metrics\ndata: {metrics_data}\n\n"

            # Send chunk scores
            for score in response.chunk_scores:
                score_data = json.dumps(score.model_dump())
                yield f"event: chunk\ndata: {score_data}\n\n"

            # Stream answer text (word by word for streaming feel)
            words = response.response_text.split()
            for i, word in enumerate(words):
                separator = " " if i > 0 else ""
                yield f"event: answer\ndata: {json.dumps({'text': separator + word})}\n\n"

            # Send citations
            citations_data = json.dumps([c.model_dump() for c in response.citations])
            yield f"event: citations\ndata: {citations_data}\n\n"

            # Done
            done_data = json.dumps({
                "query_id": str(response.query_id),
                "total_ms": response.timing.total_ms,
            })
            yield f"event: done\ndata: {done_data}\n\n"

        except Exception as e:
            error_data = json.dumps({
                "code": "QUERY_FAILED",
                "message": str(e),
            })
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )


@router.get("/{query_id}/replay", response_model=ApiResponse[dict])
async def replay_query(
    query_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """
    WHAT: Replay a previous query by its ID.
    WHY: Deterministic query replay enables debugging and auditability.
         Reconstructs the full pipeline view from stored telemetry.
    """
    repo = QueryLogRepository(session)
    query_log = await repo.get_by_id(query_id)

    if query_log is None:
        return ApiResponse.fail(
            code="RECORD_NOT_FOUND",
            message=f"Query log {query_id} not found",
        )

    return ApiResponse.ok({
        "query_text": query_log.query_text,
        "intent": query_log.intent,
        "response_text": query_log.response_text,
        "confidence_score": query_log.confidence_score,
        "confidence_breakdown": query_log.confidence_breakdown,
        "contradictions": query_log.contradictions_detected,
        "retrieved_chunk_ids": query_log.retrieved_chunk_ids,
        "vector_scores": query_log.vector_scores,
        "bm25_scores": query_log.bm25_scores,
        "combined_scores": query_log.combined_scores,
        "reranker_scores": query_log.reranker_scores,
        "timing": {
            "intent_time_ms": query_log.intent_time_ms,
            "retrieval_time_ms": query_log.retrieval_time_ms,
            "rerank_time_ms": query_log.rerank_time_ms,
            "llm_time_ms": query_log.llm_time_ms,
            "total_time_ms": query_log.total_time_ms,
        },
        "model_versions": {
            "embedding": query_log.embedding_model_version,
            "reranker": query_log.reranker_model_version,
            "llm": query_log.llm_model_version,
        },
        "feature_flags_snapshot": query_log.feature_flags_snapshot,
        "request_id": query_log.request_id,
        "created_at": query_log.created_at.isoformat() if query_log.created_at else None,
    })
