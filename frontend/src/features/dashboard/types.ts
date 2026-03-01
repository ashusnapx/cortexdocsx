import { z } from "zod";

export const DocumentResponseSchema = z.object({
  id: z.string(),
  original_filename: z.string(),
  status: z.enum(["PENDING", "PROCESSING", "COMPLETED", "FAILED"]),
  page_count: z.number().nullable(),
  chunk_count: z.number().nullable(),
  error_message: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const ListDocumentsResponseSchema = z.object({
  success: z.boolean(),
  data: z
    .object({
      documents: z.array(DocumentResponseSchema),
    })
    .nullable(),
  error: z
    .object({
      code: z.string(),
      message: z.string(),
    })
    .nullable(),
});

export const UploadResponseSchema = z.object({
  success: z.boolean(),
  data: z
    .object({
      ingestion_job: z.object({
        id: z.string(),
        status: z.string(),
        document_id: z.string(),
        page_count: z.number().nullable(),
        chunk_count: z.number().nullable(),
      }),
      timing: z.object({
        total_ms: z.number(),
        stages: z.array(
          z.object({
            stage: z.string(),
            duration_ms: z.number(),
          }),
        ),
      }),
    })
    .nullable(),
  error: z
    .object({
      code: z.string(),
      message: z.string(),
    })
    .nullable(),
});

export type DocumentResponse = z.infer<typeof DocumentResponseSchema>;
export type ListDocumentsResponse = z.infer<typeof ListDocumentsResponseSchema>;
export type UploadResponse = z.infer<typeof UploadResponseSchema>;
