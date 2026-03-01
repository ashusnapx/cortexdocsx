"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Citation } from "../types";
import { Badge } from "@/shared/ui/badge";
import { FileText, ExternalLink } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface StreamingResponseProps {
  text: string;
  isStreaming: boolean;
  citations?: Citation[];
}

export function StreamingResponse({
  text,
  isStreaming,
  citations,
}: StreamingResponseProps) {
  return (
    <div className='flex flex-col gap-8'>
      {/* Markdown Body */}
      <div className='prose prose-sm md:prose-base prose-gray max-w-none dark:prose-invert'>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: ({ node, ...props }) => (
              <a
                {...props}
                className='text-primary hover:underline font-medium'
              />
            ),
            code: ({ inline, className, children, ...props }: any) => {
              const match = /language-(\w+)/.exec(className || "");
              return !inline ?
                  <div className='relative rounded-lg bg-gray-900 group'>
                    <pre className='overflow-x-auto p-4 text-sm text-gray-50'>
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  </div>
                : <code
                    className='rounded bg-muted/20 px-1.5 py-0.5 text-sm font-mono text-primary'
                    {...props}
                  >
                    {children}
                  </code>;
            },
          }}
        >
          {text + (isStreaming ? " █" : "")}
        </ReactMarkdown>
      </div>

      {/* Citations Grid */}
      <AnimatePresence>
        {!isStreaming && citations && citations.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className='flex flex-col gap-4 border-t border-border pt-6'
          >
            <h4 className='text-sm font-semibold text-foreground flex items-center gap-2'>
              <FileText className='h-4 w-4 text-muted-foreground' />
              Sources Referenced
            </h4>
            <div className='grid gap-3 sm:grid-cols-2 lg:grid-cols-3'>
              {citations.map((citation, i) => (
                <div
                  key={citation.id || i}
                  className='group flex flex-col justify-between gap-2 rounded-lg border border-border bg-surface p-3 transition-colors hover:border-primary/50'
                  title={citation.chunk_preview}
                >
                  <div className='flex items-start justify-between gap-2'>
                    <p className='line-clamp-2 text-xs font-medium text-foreground'>
                      {citation.document_name}
                    </p>
                    <ExternalLink className='h-3 w-3 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100' />
                  </div>
                  <div className='flex items-center justify-between'>
                    <span className='text-[10px] text-muted-foreground'>
                      {citation.page_number ?
                        `Page ${citation.page_number}`
                      : "Extracted Context"}
                    </span>
                    <Badge
                      variant='secondary'
                      className='text-[10px] py-0 px-1.5'
                    >
                      {(citation.relevance_score * 100).toFixed(1)}% Match
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
