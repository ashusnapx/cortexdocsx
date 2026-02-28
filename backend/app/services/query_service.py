"""
WHAT: Query orchestration service — the full query-to-answer pipeline.
WHY: Single service that coordinates intent classification, hybrid retrieval,
     reranking, context compression, confidence scoring, contradiction detection,
     and LLM generation. Returns full transparency data for the UI.
WHEN: Called by the query API route for every user query.
WHERE: backend/app/services/query_service.py
HOW: Sequential pipeline with per-stage timing. Adaptive retrieval on low confidence.
     Full telemetry stored in QueryLog for replay.
ALTERNATIVES CONSIDERED:
  - LangChain Agent: Too much abstraction, less control over pipeline stages.
  - Separate microservices per stage: Premature distribution for local deployment.
TRADEOFFS:
  - Sequential pipeline adds latency vs. potential parallel execution of some stages.
  - Full telemetry storage per query costs ~2-5KB per query — acceptable.
  - Context compression by score ranking may drop relevant lower-scored chunks.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import (
    CHARS_PER_TOKEN_ESTIMATE,
    INTENT_PROMPT_TEMPLATES,
    QueryIntent,
)
from app.core.features import get_feature_flags
from app.domain.models import QueryLog
from app.infrastructure.llm_provider import MockLLMProvider, OpenAICompatibleProvider
from app.observability.timing import PipelineTimer, timed_stage
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.query_log_repo import QueryLogRepository
from app.schemas.query import (
    ChunkScore,
    Citation,
    ConfidenceBreakdown,
    QueryResponse,
    RetrievalMetrics,
)
from app.services.confidence_service import ConfidenceService
from app.services.intent_service import IntentService
from app.services.reranking_service import RerankingService
from app.services.retrieval_service import RetrievalService

logger = structlog.get_logger(__name__)


class QueryService:
    """
    WHAT: Full query-to-answer pipeline orchestrator.
    WHY: Coordinates all retrieval and intelligence stages with observability.
    """

    def __init__(
        self,
        session: AsyncSession,
        retrieval_service: RetrievalService,
        reranking_service: RerankingService,
        confidence_service: ConfidenceService,
        intent_service: IntentService,
        llm_provider: MockLLMProvider | OpenAICompatibleProvider,
        chunk_repo: ChunkRepository,
        query_log_repo: QueryLogRepository,
    ) -> None:
        self._session = session
        self._retrieval = retrieval_service
        self._reranking = reranking_service
        self._confidence = confidence_service
        self._intent = intent_service
        self._llm = llm_provider
        self._chunk_repo = chunk_repo
        self._query_log_repo = query_log_repo
        self._settings = get_settings()

    async def execute_query(
        self,
        query: str,
        request_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        top_k: Optional[int] = None,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
        enable_reranking: Optional[bool] = None,
        enable_hybrid: Optional[bool] = None,
        intent_override: Optional[str] = None,
    ) -> QueryResponse:
        """
        WHAT: Execute the full query pipeline and return a comprehensive response.
        WHY: Main entry point for user queries with full transparency data.

        Pipeline:
        1. Intent classification
        2. Hybrid retrieval (vector + BM25)
        3. Cross-encoder reranking
        4. Context budget optimization
        5. Confidence scoring + contradiction detection
        6. LLM generation
        7. Query logging
        """
        timer = PipelineTimer()
        timer.start()
        flags = get_feature_flags()
        query_id = uuid.uuid4()

        # ── Stage 1: Intent Classification ──
        async with timed_stage(timer, "intent_classification") as ctx:
            if intent_override:
                intent = QueryIntent(intent_override)
            elif flags.ENABLE_INTENT_CLASSIFICATION:
                intent = self._intent.classify(query)
            else:
                intent = QueryIntent.PRECISE
            ctx["intent"] = intent.value

        # ── Stage 2: Hybrid Retrieval ──
        async with timed_stage(timer, "hybrid_retrieval") as ctx:
            retrieval_results = await self._retrieval.retrieve(
                query, top_k=top_k, alpha=alpha, beta=beta
            )
            ctx["result_count"] = len(retrieval_results)

        # Fetch actual chunk content from DB
        vector_store_ids = [r["vector_store_id"] for r in retrieval_results]
        chunks_db = await self._chunk_repo.get_by_vector_store_ids(vector_store_ids)
        chunks_map = {c.vector_store_id: c for c in chunks_db}

        # Enrich retrieval results with chunk content
        enriched_chunks = []
        for result in retrieval_results:
            vsid = result["vector_store_id"]
            chunk = chunks_map.get(vsid)
            if chunk:
                enriched_chunks.append({
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "document_name": chunk.document.original_filename if chunk.document else "Unknown",
                    "page_number": chunk.page_number,
                    "content": chunk.content,
                    "vector_score": result["vector_score"],
                    "bm25_score": result["bm25_score"],
                    "combined_score": result["combined_score"],
                    "reranker_score": None,
                    "final_score": result["combined_score"],
                })

        # ── Stage 3: Reranking ──
        use_reranking = enable_reranking if enable_reranking is not None else flags.ENABLE_RERANKING
        if use_reranking and enriched_chunks:
            async with timed_stage(timer, "reranking") as ctx:
                enriched_chunks = await self._reranking.rerank(
                    query,
                    enriched_chunks,
                    top_k=self._settings.RERANKER_TOP_K,
                )
                # Update final scores to use reranker score
                for chunk in enriched_chunks:
                    chunk["final_score"] = chunk.get("reranker_score", chunk["combined_score"])
                ctx["reranked_count"] = len(enriched_chunks)

        # ── Stage 4: Context Budget Optimization ──
        async with timed_stage(timer, "context_trimming") as ctx:
            trimmed_chunks, token_budget_used = self._optimize_context_budget(enriched_chunks)
            ctx["chunks_kept"] = len(trimmed_chunks)
            ctx["tokens_used"] = token_budget_used

        # ── Stage 5: Confidence Scoring + Contradiction Detection ──
        async with timed_stage(timer, "confidence_scoring") as ctx:
            if flags.ENABLE_CONFIDENCE_SCORING:
                confidence = self._confidence.compute_confidence(trimmed_chunks, query)
            else:
                confidence = ConfidenceBreakdown(
                    overall=0.0, similarity_component=0.0,
                    reranker_component=0.0, agreement_component=0.0,
                    dispersion_component=0.0,
                )

            contradictions = []
            if flags.ENABLE_CONTRADICTION_DETECTION:
                contradictions = self._confidence.detect_contradictions(trimmed_chunks)

            ctx["confidence"] = confidence.overall
            ctx["contradictions_count"] = len(contradictions)

        # ── Adaptive Retrieval (if confidence is low) ──
        if (
            flags.ENABLE_ADAPTIVE_RETRIEVAL
            and confidence.overall < self._settings.ADAPTIVE_CONFIDENCE_THRESHOLD
            and len(enriched_chunks) > 0
        ):
            logger.info(
                "adaptive_retrieval_triggered",
                confidence=confidence.overall,
                threshold=self._settings.ADAPTIVE_CONFIDENCE_THRESHOLD,
            )
            expanded_top_k = int(
                (top_k or self._settings.RETRIEVAL_TOP_K)
                * self._settings.ADAPTIVE_TOP_K_MULTIPLIER
            )
            async with timed_stage(timer, "adaptive_retrieval") as ctx:
                expanded_results = await self._retrieval.retrieve(
                    query, top_k=expanded_top_k, alpha=alpha, beta=beta
                )
                ctx["expanded_count"] = len(expanded_results)

        # ── Stage 6: LLM Generation ──
        async with timed_stage(timer, "llm_generation") as ctx:
            context_text = self._build_context(trimmed_chunks)
            system_prompt = INTENT_PROMPT_TEMPLATES.get(
                intent.value, INTENT_PROMPT_TEMPLATES["precise"]
            )
            prompt = self._build_prompt(query, context_text, contradictions)
            response_text = await self._llm.generate(
                prompt, system_prompt, self._settings.LLM_MAX_TOKENS
            )
            ctx["response_length"] = len(response_text)

        # ── Build Response ──
        chunk_scores = [
            ChunkScore(
                chunk_id=c["chunk_id"],
                document_id=c["document_id"],
                document_name=c["document_name"],
                page_number=c["page_number"],
                content_preview=c["content"][:500],
                vector_score=c["vector_score"],
                bm25_score=c["bm25_score"],
                combined_score=c["combined_score"],
                reranker_score=c.get("reranker_score"),
                final_score=c["final_score"],
            )
            for c in enriched_chunks
        ]

        citations = [
            Citation(
                document_name=c["document_name"],
                page_number=c["page_number"],
                chunk_preview=c["content"][:200],
                relevance_score=c["final_score"],
            )
            for c in trimmed_chunks
        ]

        retrieval_metrics = RetrievalMetrics(
            total_chunks_searched=self._retrieval._vector_store.total_vectors,
            vector_results_count=len([r for r in retrieval_results if r["vector_score"] > 0]),
            bm25_results_count=len([r for r in retrieval_results if r["bm25_score"] > 0]),
            reranked_count=len(enriched_chunks) if use_reranking else 0,
            final_context_chunks=len(trimmed_chunks),
            token_budget_used=token_budget_used,
            token_budget_total=self._settings.TOKEN_BUDGET,
        )

        from app.schemas.common import PipelineTiming, TimingStage
        pipeline_timing = PipelineTiming(
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

        response = QueryResponse(
            query_id=query_id,
            query_text=query,
            intent=intent.value,
            response_text=response_text,
            chunk_scores=chunk_scores,
            confidence=confidence,
            contradictions=contradictions,
            citations=citations,
            retrieval_metrics=retrieval_metrics,
            timing=pipeline_timing,
            model_versions={
                "embedding": self._retrieval._embedding_service.model_name,
                "reranker": self._reranking.model_name if use_reranking else "disabled",
                "llm": self._settings.LLM_MODEL_NAME,
            },
            feature_flags={
                "hybrid_search": flags.ENABLE_HYBRID_SEARCH,
                "reranking": bool(use_reranking),
                "contradiction_detection": flags.ENABLE_CONTRADICTION_DETECTION,
                "adaptive_retrieval": flags.ENABLE_ADAPTIVE_RETRIEVAL,
                "confidence_scoring": flags.ENABLE_CONFIDENCE_SCORING,
            },
        )

        # ── Stage 7: Query Logging ──
        if flags.ENABLE_QUERY_LOGGING:
            try:
                query_log = QueryLog(
                    query_text=query,
                    intent=intent.value,
                    response_text=response_text,
                    confidence_score=confidence.overall,
                    retrieved_chunk_ids=[c.chunk_id for c in chunk_scores],
                    vector_scores=[c.vector_score for c in chunk_scores],
                    bm25_scores=[c.bm25_score for c in chunk_scores],
                    combined_scores=[c.combined_score for c in chunk_scores],
                    reranker_scores=[c.reranker_score for c in chunk_scores if c.reranker_score],
                    final_chunk_ids=[c.chunk_id for c in chunk_scores[:len(trimmed_chunks)]],
                    confidence_breakdown=confidence.model_dump(),
                    contradictions_detected=[c.model_dump() for c in contradictions],
                    intent_time_ms=timer.stages[0].duration_ms if timer.stages else None,
                    retrieval_time_ms=timer.stages[1].duration_ms if len(timer.stages) > 1 else None,
                    rerank_time_ms=next(
                        (s.duration_ms for s in timer.stages if s.stage == "reranking"), None
                    ),
                    llm_time_ms=next(
                        (s.duration_ms for s in timer.stages if s.stage == "llm_generation"), None
                    ),
                    total_time_ms=timer.total_ms,
                    embedding_model_version=self._retrieval._embedding_service.model_name,
                    reranker_model_version=self._reranking.model_name,
                    llm_model_version=self._settings.LLM_MODEL_NAME,
                    feature_flags_snapshot=response.feature_flags,
                    request_id=request_id,
                    client_ip=client_ip,
                )
                await self._query_log_repo.create(query_log)
                await self._session.commit()
            except Exception as e:
                logger.error("query_log_save_failed", error=str(e))

        return response

    def _optimize_context_budget(
        self, chunks: list[dict]
    ) -> tuple[list[dict], int]:
        """
        WHAT: Score-based context budget optimization.
        WHY: Instead of naive truncation, includes chunks by relevance score
             until the token budget is exhausted. Higher-scored chunks contribute
             more information per token.
        Returns: (trimmed chunks, total tokens used)
        """
        budget = self._settings.TOKEN_BUDGET
        selected: list[dict] = []
        tokens_used = 0

        sorted_chunks = sorted(
            chunks, key=lambda c: c.get("final_score", 0), reverse=True
        )

        for chunk in sorted_chunks:
            chunk_tokens = max(
                1, int(len(chunk.get("content", "")) / CHARS_PER_TOKEN_ESTIMATE)
            )
            if tokens_used + chunk_tokens <= budget:
                selected.append(chunk)
                tokens_used += chunk_tokens
            else:
                break

        return selected, tokens_used

    def _build_context(self, chunks: list[dict]) -> str:
        """Build a formatted context string from selected chunks."""
        context_parts: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            doc_name = chunk.get("document_name", "Unknown")
            page = chunk.get("page_number", 0)
            content = chunk.get("content", "")
            context_parts.append(
                f"[Source {i}: {doc_name}, Page {page}]\n{content}\n"
            )
        return "\n".join(context_parts)

    def _build_prompt(
        self,
        query: str,
        context: str,
        contradictions: list,
    ) -> str:
        """Build the user prompt with context and contradiction warnings."""
        parts = [f"Context:\n{context}\n"]

        if contradictions:
            parts.append(
                "⚠️ WARNING: The following numerical contradictions were detected "
                "across the source documents:\n"
            )
            for c in contradictions:
                parts.append(
                    f"  - {c.entity}: '{c.value_a}' ({c.source_a}) vs "
                    f"'{c.value_b}' ({c.source_b})\n"
                )
            parts.append(
                "Please acknowledge these discrepancies in your response.\n"
            )

        parts.append(f"\nQuestion: {query}")
        return "\n".join(parts)
