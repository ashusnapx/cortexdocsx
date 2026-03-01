import { useState, useCallback, useRef } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { QueryRequestPayload, QueryResponse } from "../types";
import { toast } from "sonner";

export function useQueryStream() {
  const [streamedAnswer, setStreamedAnswer] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const [finalResponse, setFinalResponse] = useState<QueryResponse | null>(
    null,
  );

  const abortControllerRef = useRef<AbortController | null>(null);

  const triggerQuery = useCallback(
    (payload: QueryRequestPayload) => {
      setIsQuerying(true);
      setStreamedAnswer("");
      setFinalResponse(null);

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const ctrl = new AbortController();
      abortControllerRef.current = ctrl;

      const API_BASE_URL =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

      // We build the response progressively as SSE yields telemetry chunks
      const aggregatedResponse: Partial<QueryResponse> = {
        query: payload.query,
        response_text: "",
        citations: [],
        chunk_scores: [],
        timing: { total_ms: 0, stages: [] },
      };

      fetchEventSource(`${API_BASE_URL}/query/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        signal: ctrl.signal,
        openWhenHidden: true,
        async onopen(response) {
          if (response.ok) {
            console.log("SSE connection opened");
            return;
          } else if (
            response.status >= 400 &&
            response.status < 500 &&
            response.status !== 429
          ) {
            throw new Error(`Failed to connect: ${response.status}`);
          }
        },
        onmessage(msg) {
          try {
            const data = JSON.parse(msg.data);

            if (msg.event === "stage") {
              aggregatedResponse.timing!.stages.push({
                stage: data.stage,
                duration_ms: data.duration_ms,
              });
            } else if (msg.event === "metrics") {
              aggregatedResponse.confidence = data.confidence;
              aggregatedResponse.retrieval_metrics = data.retrieval_metrics;
              aggregatedResponse.contradictions = data.contradictions;
            } else if (msg.event === "chunk") {
              aggregatedResponse.chunk_scores!.push(data);
            } else if (msg.event === "answer") {
              const text = data.text || "";
              setStreamedAnswer((prev) => prev + text);
              aggregatedResponse.response_text += text;
            } else if (msg.event === "citations") {
              aggregatedResponse.citations = data;
            } else if (msg.event === "done") {
              aggregatedResponse.response_id = data.query_id;
              aggregatedResponse.timing!.total_ms = data.total_ms;

              setFinalResponse(aggregatedResponse as QueryResponse);
              setIsQuerying(false);
              ctrl.abort(); // Close stream gracefully
            } else if (msg.event === "error") {
              toast.error(
                data.message || "An error occurred during query execution",
              );
              setIsQuerying(false);
              ctrl.abort();
            }
          } catch (err) {
            console.error("Error parsing SSE message:", err);
          }
        },
        onclose() {
          // Only set false if we haven't already finished successfully
          if (isQuerying) {
            setIsQuerying(false);
          }
        },
        onerror(err) {
          toast.error(
            err.message || "Failed to establish streaming connection.",
          );
          setIsQuerying(false);
          throw err; // Stop fetchEventSource from automatically retrying
        },
      });
    },
    [isQuerying],
  );

  const abortQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsQuerying(false);
    }
  }, []);

  return {
    streamedAnswer,
    isQuerying,
    finalResponse,
    triggerQuery,
    abortQuery,
  };
}
