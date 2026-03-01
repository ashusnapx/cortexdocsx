import { z } from "zod";

export const ConfigSchema = z.object({
  hyperparameters: z.object({
    alpha: z.object({
      min: z.number(),
      max: z.number(),
      default: z.number(),
      step: z.number(),
      description: z.string(),
    }),
    beta: z.object({
      min: z.number(),
      max: z.number(),
      default: z.number(),
      step: z.number(),
      description: z.string(),
    }),
    reranking: z.object({
      default: z.boolean(),
      description: z.string(),
    }),
    hybrid: z.object({
      default: z.boolean(),
      description: z.string(),
    }),
  }),
  limits: z.object({
    max_file_size_mb: z.number(),
    max_pages: z.number(),
  }),
});

export type AppConfig = z.infer<typeof ConfigSchema>;

// Fallback config mimicking a backend response in case the endpoint fails or during dev mock
export const MOCK_APP_CONFIG: AppConfig = {
  hyperparameters: {
    alpha: {
      min: 0,
      max: 1,
      step: 0.01,
      default: 0.7,
      description: "Vector search weight",
    },
    beta: {
      min: 0,
      max: 1,
      step: 0.01,
      default: 0.3,
      description: "Keyword search weight (BM25)",
    },
    reranking: { default: true, description: "Neural cross-encoder reranking" },
    hybrid: {
      default: true,
      description: "Combine dense and sparse retrieval",
    },
  },
  limits: { max_file_size_mb: 50, max_pages: 500 },
};
