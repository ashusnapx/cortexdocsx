"use client";

import { QueryResponse } from "../../query/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/shared/ui/card";
import { Badge } from "@/shared/ui/badge";
import { Activity, Clock, Target, Scale, Zap } from "lucide-react";
import { motion } from "framer-motion";

interface TransparencyPanelProps {
  response: QueryResponse | null;
  isQuerying: boolean;
}

export function TransparencyPanel({
  response,
  isQuerying,
}: TransparencyPanelProps) {
  if (isQuerying) {
    return (
      <Card className='animate-pulse border-border bg-background'>
        <div className='flex h-32 flex-col items-center justify-center gap-3'>
          <Activity className='h-6 w-6 text-muted-foreground animate-bounce' />
          <p className='text-sm font-medium text-muted-foreground'>
            Gathering Telemetry...
          </p>
        </div>
      </Card>
    );
  }

  if (!response) {
    return (
      <Card className='border-dashed border-border bg-surface/50'>
        <div className='flex h-32 flex-col items-center justify-center gap-2 text-center text-muted-foreground'>
          <Scale className='h-6 w-6 opacity-20' />
          <p className='text-sm'>
            Run a query to inspect the retrieval pipeline.
          </p>
        </div>
      </Card>
    );
  }

  const { confidence, timing, retrieval_metrics } = response;
  const overallConf = (confidence.overall * 100).toFixed(1);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className='grid gap-6 lg:grid-cols-3'
    >
      {/* Confidence Score Panel */}
      <Card className='border-border bg-background shadow-sm lg:col-span-1 border-t-4 border-t-primary'>
        <CardHeader className='pb-2'>
          <CardTitle className='flex items-center gap-2 text-base font-medium'>
            <Target className='h-4 w-4 text-primary' />
            Confidence Score
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className='flex flex-col items-center justify-center py-4'>
            <div className='text-4xl font-bold tracking-tight text-foreground'>
              {overallConf}
              <span className='text-2xl text-muted-foreground'>%</span>
            </div>
            <p className='mt-2 text-xs text-muted-foreground text-center'>
              Algorithmic trust derived from semantic agreement and dispersion.
            </p>
          </div>
          <div className='mt-4 grid grid-cols-2 gap-2 text-xs'>
            <div className='flex justify-between rounded bg-surface px-2 py-1'>
              <span className='text-muted-foreground'>Similarity</span>
              <span className='font-mono text-foreground'>
                {(confidence.similarity_component * 100).toFixed(0)}%
              </span>
            </div>
            <div className='flex justify-between rounded bg-surface px-2 py-1'>
              <span className='text-muted-foreground'>Agreement</span>
              <span className='font-mono text-foreground'>
                {(confidence.agreement_component * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Retrieval Metrics Panel */}
      <Card className='border-border bg-background shadow-sm lg:col-span-1'>
        <CardHeader className='pb-2'>
          <CardTitle className='flex items-center gap-2 text-base font-medium'>
            <Scale className='h-4 w-4 text-primary' />
            Retrieval Engine
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className='flex flex-col gap-3 py-2'>
            <div className='flex items-center justify-between'>
              <span className='text-sm text-muted-foreground'>
                Chunks Scanned
              </span>
              <Badge variant='outline'>
                {retrieval_metrics.total_chunks_searched}
              </Badge>
            </div>
            <div className='flex items-center justify-between'>
              <span className='text-sm text-muted-foreground'>
                Vector Matches
              </span>
              <span className='text-sm font-medium text-foreground'>
                {retrieval_metrics.vector_results_count}
              </span>
            </div>
            <div className='flex items-center justify-between'>
              <span className='text-sm text-muted-foreground'>
                BM25 Matches
              </span>
              <span className='text-sm font-medium text-foreground'>
                {retrieval_metrics.bm25_results_count}
              </span>
            </div>
            <div className='flex items-center justify-between border-t border-border pt-2'>
              <span className='text-sm font-medium text-foreground'>
                Final Context Size
              </span>
              <Badge variant='secondary' className='bg-primary/10 text-primary'>
                {retrieval_metrics.final_context_chunks} chunks
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Latency & Timing Panel */}
      <Card className='border-border bg-background shadow-sm lg:col-span-1'>
        <CardHeader className='pb-2'>
          <CardTitle className='flex items-center gap-2 text-base font-medium'>
            <Zap className='h-4 w-4 text-primary' />
            Pipeline Latency
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className='flex flex-col gap-3 py-2'>
            <div className='flex items-center justify-between border-b border-border pb-2'>
              <span className='text-sm font-medium text-foreground flex items-center gap-1.5'>
                <Clock className='h-3.5 w-3.5' /> Total Time
              </span>
              <span className='font-mono text-sm font-bold text-foreground'>
                {(timing.total_ms / 1000).toFixed(2)}s
              </span>
            </div>

            <div className='flex flex-col gap-2 mt-1'>
              {timing.stages.map((stage, i) => (
                <div key={i} className='flex flex-col gap-1'>
                  <div className='flex justify-between text-xs'>
                    <span className='text-muted-foreground capitalize'>
                      {stage.stage.replace(/_/g, " ")}
                    </span>
                    <span className='font-mono text-muted-foreground'>
                      {stage.duration_ms}ms
                    </span>
                  </div>
                  <div className='h-1.5 w-full overflow-hidden rounded-full bg-surface'>
                    <div
                      className='h-full bg-primary/70 rounded-full'
                      style={{
                        width: `${Math.max(2, (stage.duration_ms / timing.total_ms) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
