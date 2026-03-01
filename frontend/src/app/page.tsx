"use client";

import { DocumentUploader } from "@/features/dashboard/components/DocumentUploader";
import { DynamicQueryPanel } from "@/features/dashboard/components/DynamicQueryPanel";
import { QueryPanel } from "@/features/query/components/QueryPanel";
import { TransparencyPanel } from "@/features/transparency/components/TransparencyPanel";
import { useQueryStream } from "@/features/query/hooks/useQueryStream";
import { Badge } from "@/shared/ui/badge";

export default function Home() {
  const { isQuerying, finalResponse } = useQueryStream();

  return (
    <div className='mx-auto flex w-full max-w-[1200px] flex-col gap-12 px-6 py-12 md:py-20 lg:flex-row lg:items-start lg:gap-16'>
      {/* Left Column (Main App Core) */}
      <div className='flex w-full flex-col gap-12 lg:w-3/5'>
        {/* Header Hero */}
        <div className='flex flex-col gap-4'>
          <Badge className='w-fit'>App Dashboard</Badge>
          <h1 className='text-4xl font-bold tracking-tight text-foreground md:text-5xl'>
            Sovereign Intelligence
          </h1>
          <p className='max-w-[480px] text-lg text-muted-foreground leading-relaxed'>
            Upload proprietary documents, tune retrieval boundaries, and inspect
            AI confidence telemetry directly on-device.
          </p>
        </div>

        {/* The Generative Search UI */}
        <section className='flex flex-col gap-6' id='search'>
          <div className='flex items-center justify-between'>
            <h2 className='text-xl font-semibold tracking-tight text-foreground'>
              Query Engine
            </h2>
          </div>
          <QueryPanel />
        </section>

        {/* Transparency / Telemetry Output */}
        {(finalResponse || isQuerying) && (
          <section className='flex flex-col gap-6' id='transparency'>
            <div className='flex items-center justify-between border-t border-border pt-12'>
              <h2 className='text-xl font-semibold tracking-tight text-foreground'>
                Retrieval Telemetry
              </h2>
            </div>
            <TransparencyPanel
              response={finalResponse}
              isQuerying={isQuerying}
            />
          </section>
        )}
      </div>

      {/* Right Column (Sidebar Configuration & Ingestion) */}
      <aside className='flex w-full flex-col gap-8 lg:sticky lg:top-24 lg:w-2/5'>
        <div className='flex flex-col gap-4'>
          <h3 className='text-lg font-semibold tracking-tight text-foreground'>
            Ingestion Pipeline
          </h3>
          <DocumentUploader />
        </div>

        <div className='flex flex-col gap-4'>
          <h3 className='text-lg font-semibold tracking-tight text-foreground'>
            System Tuning
          </h3>
          <DynamicQueryPanel />
        </div>
      </aside>
    </div>
  );
}
