import { z } from "zod";

// Citation source mapping
export const CitationSchema = z.object({
  id: z.string(),
  document_name: z.string(),
  page_number: z.number().nullable(),
  chunk_preview: z.string(),
  relevance_score: z.number(),
});

// Explicit chunk scoring telemetry
export const ChunkScoreSchema = z.object({
  chunk_id: z.string(),
  document_name: z.string(),
  page_number: z.number().nullable(),
  vector_score: z.number(),
  bm25_score: z.number(),
  final_score: z.number(),
  reranker_score: z.number().nullable(),
  reranked_position: z.number().nullable(),
});

// Confidence breakdown algorithm output
export const ConfidenceBreakdownSchema = z.object({
  overall: z.number(),
  similarity_component: z.number(),
  reranker_component: z.number(),
  agreement_component: z.number(),
  dispersion_component: z.number(),
});

// Pipeline timing stages
export const TimingStageSchema = z.object({
  stage: z.string(),
  duration_ms: z.number(),
});

export const RetrievalMetricsSchema = z.object({
  total_chunks_searched: z.number(),
  vector_results_count: z.number(),
  bm25_results_count: z.number(),
  reranked_count: z.number(),
  final_context_chunks: z.number(),
  token_budget_used: z.number(),
  token_budget_total: z.number(),
});

// The final massive telemetry object returned when the stream finishes
export const QueryResponseSchema = z.object({
  response_id: z.string(),
  query: z.string(),
  response_text: z.string(),
  citations: z.array(CitationSchema),
  confidence: ConfidenceBreakdownSchema,
  chunk_scores: z.array(ChunkScoreSchema),
  retrieval_metrics: RetrievalMetricsSchema,
  timing: z.object({
    total_ms: z.number(),
    stages: z.array(TimingStageSchema),
  }),
  contradictions: z
    .array(
      z.object({
        issue: z.string(),
        sources: z.array(z.string()),
      }),
    )
    .optional(),
});

export type Citation = z.infer<typeof CitationSchema>;
export type ChunkScore = z.infer<typeof ChunkScoreSchema>;
export type ConfidenceBreakdown = z.infer<typeof ConfidenceBreakdownSchema>;
export type TimingStage = z.infer<typeof TimingStageSchema>;
export type RetrievalMetrics = z.infer<typeof RetrievalMetricsSchema>;
export type QueryResponse = z.infer<typeof QueryResponseSchema>;

// Input payload to the backend
export const QueryRequestSchema = z.object({
  query: z.string(),
  alpha: z.number().optional(),
  beta: z.number().optional(),
  enable_reranking: z.boolean().optional(),
  enable_hybrid: z.boolean().optional(),
});
export type QueryRequestPayload = z.infer<typeof QueryRequestSchema>;
