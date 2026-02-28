/**
 * WHAT: API client for CortexDocs ∞ backend communication.
 * WHY: Centralizes all HTTP calls with error handling and type safety.
 */

import type {
  ApiResponse,
  DocumentListResponse,
  HealthResponse,
  QueryRequest,
  QueryResponse,
  UploadResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

async function apiFetch<T>(
  url: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });
  return response.json();
}

export async function uploadDocument(
  file: File,
): Promise<ApiResponse<UploadResponse>> {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch<UploadResponse>(`${API_V1}/documents/upload`, {
    method: "POST",
    body: formData,
  });
}

export async function listDocuments(
  offset = 0,
  limit = 50,
): Promise<ApiResponse<DocumentListResponse>> {
  return apiFetch<DocumentListResponse>(
    `${API_V1}/documents?offset=${offset}&limit=${limit}`,
  );
}

export async function executeQuery(
  request: QueryRequest,
): Promise<ApiResponse<QueryResponse>> {
  return apiFetch<QueryResponse>(`${API_V1}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export async function fetchHealth(): Promise<ApiResponse<HealthResponse>> {
  return apiFetch<HealthResponse>(`${API_V1}/health`);
}

export function createSSEConnection(request: QueryRequest): EventSource | null {
  // SSE via POST requires a custom approach since EventSource only supports GET
  // We use fetch with streaming for POST-based SSE
  return null;
}

export async function* streamQuery(
  request: QueryRequest,
): AsyncGenerator<{ event: string; data: unknown }> {
  const response = await fetch(`${API_V1}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7);
      } else if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          yield { event: currentEvent, data };
        } catch {
          // Skip malformed JSON
        }
      }
    }
  }
}

export async function replayQuery(
  queryId: string,
): Promise<ApiResponse<unknown>> {
  return apiFetch<unknown>(`${API_V1}/query/${queryId}/replay`);
}
