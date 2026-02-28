"""
WHAT: Pydantic schemas for query API endpoints.
WHY: Defines the full query request/response contract including all transparency data:
     scores, confidence breakdown, contradictions, citations, and pipeline timing.
WHEN: Used by query API routes and SSE streaming endpoint.
WHERE: backend/app/schemas/query.py
HOW: Nested models for each transparency section (retrieval, confidence, citations).
ALTERNATIVES CONSIDERED: Flat response — rejected for poor UI mapping.
TRADEOFFS: Deeply nested response adds serialization cost but maps cleanly to UI panels.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PipelineTiming


class QueryRequest(BaseModel):
    """Request schema for a user query."""
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: Optional[int] = Field(default=None, ge=1, le=50)
    alpha: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    beta: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    enable_reranking: Optional[bool] = None
    enable_hybrid: Optional[bool] = None
    intent_override: Optional[str] = Field(default=None, pattern="^(precise|summary|analytical)$")


class ChunkScore(BaseModel):
    """Score breakdown for a single retrieved chunk."""
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    content_preview: str = Field(..., max_length=500)
    vector_score: float = 0.0
    bm25_score: float = 0.0
    combined_score: float = 0.0
    reranker_score: Optional[float] = None
    final_score: float = 0.0


class ConfidenceBreakdown(BaseModel):
    """Detailed confidence score breakdown."""
    overall: float = Field(..., ge=0.0, le=1.0)
    similarity_component: float = 0.0
    reranker_component: float = 0.0
    agreement_component: float = 0.0
    dispersion_component: float = 0.0


class Contradiction(BaseModel):
    """A detected contradiction between chunks."""
    entity: str
    value_a: str
    source_a: str
    value_b: str
    source_b: str
    severity: str = "warning"


class Citation(BaseModel):
    """A source citation for the generated response."""
    document_name: str
    page_number: int
    chunk_preview: str
    relevance_score: float


class RetrievalMetrics(BaseModel):
    """Retrieval stage metrics for the transparency UI."""
    total_chunks_searched: int = 0
    vector_results_count: int = 0
    bm25_results_count: int = 0
    reranked_count: int = 0
    final_context_chunks: int = 0
    token_budget_used: int = 0
    token_budget_total: int = 0


class QueryResponse(BaseModel):
    """Full query response with all transparency data."""
    query_id: UUID
    query_text: str
    intent: str
    response_text: str

    # Transparency data
    chunk_scores: list[ChunkScore] = Field(default_factory=list)
    confidence: ConfidenceBreakdown
    contradictions: list[Contradiction] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    retrieval_metrics: RetrievalMetrics
    timing: PipelineTiming

    # Model versions (for replay / drift detection)
    model_versions: dict = Field(default_factory=dict)
    feature_flags: dict = Field(default_factory=dict)


class QueryReplayResponse(BaseModel):
    """Response for query replay endpoint — reconstructs full pipeline."""
    original_query: QueryResponse
    replayed_at: datetime


class SSEEvent(BaseModel):
    """Schema for a server-sent event during streaming."""
    event: str  # 'stage', 'chunk', 'answer', 'metrics', 'done', 'error'
    data: dict = Field(default_factory=dict)
