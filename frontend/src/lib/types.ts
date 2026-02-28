/**
 * WHAT: TypeScript type definitions for CortexDocs ∞ frontend.
 * WHY: Single source of truth for API response types, component props,
 *      and shared state shapes. Strict typing catches errors at compile time.
 */

// ─── API Response Envelope ────────────────────────
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ErrorDetail | null;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string;
}

// ─── Document Types ───────────────────────────────
export interface DocumentResponse {
  id: string;
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  page_count: number;
  chunk_count: number;
  created_at: string;
}

export interface IngestionJobResponse {
  id: string;
  document_id: string;
  status: string;
  error_message: string | null;
  error_code: string | null;
  retry_count: number;
  parse_time_ms: number | null;
  chunk_time_ms: number | null;
  embed_time_ms: number | null;
  index_time_ms: number | null;
  db_write_time_ms: number | null;
  total_time_ms: number | null;
  chunk_count: number;
  page_count: number;
  pipeline_metadata: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface UploadResponse {
  document: DocumentResponse;
  ingestion_job: IngestionJobResponse;
  timing: PipelineTiming | null;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
}

// ─── Query Types ──────────────────────────────────
export interface QueryRequest {
  query: string;
  top_k?: number;
  alpha?: number;
  beta?: number;
  enable_reranking?: boolean;
  enable_hybrid?: boolean;
  intent_override?: string;
}

export interface ChunkScore {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  content_preview: string;
  vector_score: number;
  bm25_score: number;
  combined_score: number;
  reranker_score: number | null;
  final_score: number;
}

export interface ConfidenceBreakdown {
  overall: number;
  similarity_component: number;
  reranker_component: number;
  agreement_component: number;
  dispersion_component: number;
}

export interface Contradiction {
  entity: string;
  value_a: string;
  source_a: string;
  value_b: string;
  source_b: string;
  severity: string;
}

export interface Citation {
  document_name: string;
  page_number: number;
  chunk_preview: string;
  relevance_score: number;
}

export interface RetrievalMetrics {
  total_chunks_searched: number;
  vector_results_count: number;
  bm25_results_count: number;
  reranked_count: number;
  final_context_chunks: number;
  token_budget_used: number;
  token_budget_total: number;
}

export interface TimingStage {
  stage: string;
  duration_ms: number;
  metadata: Record<string, unknown>;
}

export interface PipelineTiming {
  stages: TimingStage[];
  total_ms: number;
}

export interface QueryResponse {
  query_id: string;
  query_text: string;
  intent: string;
  response_text: string;
  chunk_scores: ChunkScore[];
  confidence: ConfidenceBreakdown;
  contradictions: Contradiction[];
  citations: Citation[];
  retrieval_metrics: RetrievalMetrics;
  timing: PipelineTiming;
  model_versions: Record<string, string>;
  feature_flags: Record<string, boolean>;
}

// ─── Health Types ─────────────────────────────────
export interface HealthResponse {
  database: { status: string };
  vector_store: {
    status: string;
    total_vectors: number;
    memory_usage_mb: number;
  };
  bm25_store: { status: string; total_documents: number };
  llm: {
    provider: string;
    status: string;
    circuit_breaker: CircuitBreakerStatus;
  };
  embedding_model: { status: string; model: string };
  memory: { rss_mb: number; vms_mb: number };
  app: { name: string; version: string; environment: string };
}

export interface CircuitBreakerStatus {
  state: string;
  failure_count: number;
  failure_threshold: number;
  recovery_timeout_seconds: number;
}

// ─── SSE Event Types ──────────────────────────────
export type SSEEventType =
  | "stage"
  | "metrics"
  | "chunk"
  | "answer"
  | "citations"
  | "done"
  | "error";

export interface SSEEvent {
  event: SSEEventType;
  data: unknown;
}

// ─── Pipeline Stage Names ─────────────────────────
export const PIPELINE_STAGES = {
  intent_classification: "🎯 Intent Classification",
  hybrid_retrieval: "🔍 Hybrid Retrieval",
  reranking: "🏆 Reranking",
  context_trimming: "✂️ Context Optimization",
  confidence_scoring: "📊 Confidence Scoring",
  adaptive_retrieval: "🔄 Adaptive Retrieval",
  llm_generation: "🤖 LLM Generation",
} as const;

export const INGESTION_STAGES = {
  parsing: "📄 PDF Parsing",
  chunking: "🔪 Chunking",
  embedding: "🧠 Embedding",
  indexing: "📇 FAISS Indexing",
  db_write: "💾 Database Write",
} as const;
