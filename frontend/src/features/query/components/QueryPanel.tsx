"use client";

import { useState } from "react";
import { Send, Loader2, Sparkles } from "lucide-react";
import { useQueryStream } from "../hooks/useQueryStream";
import { useAppConfig } from "../../dashboard/hooks/useDashboard";
import { Card } from "@/shared/ui/card";
import { StreamingResponse } from "./StreamingResponse";

export function QueryPanel() {
  const [query, setQuery] = useState("");
  const {
    streamedAnswer,
    isQuerying,
    finalResponse,
    triggerQuery,
    abortQuery,
  } = useQueryStream();
  const { data: config } = useAppConfig();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isQuerying) return;

    // By default, we use the active config default bounds if the user hasn't overridden them
    triggerQuery({
      query: query.trim(),
      alpha: config?.hyperparameters.alpha.default,
      beta: config?.hyperparameters.beta.default,
      enable_reranking: config?.hyperparameters.reranking.default,
      enable_hybrid: config?.hyperparameters.hybrid.default,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const hasContent = streamedAnswer.length > 0 || finalResponse;

  return (
    <div className='flex flex-col gap-6'>
      {/* Query Input */}
      <Card className='relative overflow-hidden border-primary/20 bg-surface shadow-sm focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-all duration-300'>
        <form
          onSubmit={handleSubmit}
          className='relative flex items-end gap-3 p-3'
        >
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='Ask CortexDocs a question about your indexed documents...'
            className='min-h-[56px] w-full resize-none border-0 bg-transparent py-3 pl-3 pr-12 text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50'
            rows={1}
            disabled={isQuerying}
          />
          <div className='absolute bottom-4 right-4 flex items-center gap-2'>
            {isQuerying ?
              <button
                type='button'
                onClick={abortQuery}
                className='flex h-10 w-10 items-center justify-center rounded-full bg-error text-errorForeground hover:bg-error/80 transition-colors'
                title='Stop generation'
              >
                <div className='h-3 w-3 bg-current rounded-sm' />
              </button>
            : <button
                type='submit'
                disabled={!query.trim()}
                className='flex h-10 w-10 items-center justify-center rounded-full bg-primary text-white hover:bg-primaryHover disabled:opacity-50 transition-colors'
              >
                <Send className='h-4 w-4' />
              </button>
            }
          </div>
        </form>
      </Card>

      {/* Streaming Response Area */}
      {hasContent && (
        <Card className='flex flex-col overflow-hidden border-border bg-background shadow-md'>
          <div className='flex items-center gap-2 border-b border-border bg-surface px-6 py-4'>
            {isQuerying ?
              <Loader2 className='h-5 w-5 animate-spin text-primary' />
            : <Sparkles className='h-5 w-5 text-primary' />}
            <h3 className='font-medium text-foreground'>
              {isQuerying ? "Synthesizing answer..." : "CortexDocs Analysis"}
            </h3>
          </div>

          <div className='p-6'>
            <StreamingResponse
              text={finalResponse?.response_text || streamedAnswer}
              isStreaming={isQuerying}
              citations={finalResponse?.citations}
            />
          </div>
        </Card>
      )}
    </div>
  );
}
