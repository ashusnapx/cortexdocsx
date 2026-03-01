"use client";

import { useAppConfig } from "../hooks/useDashboard";
import { Card, CardHeader, CardTitle, CardContent } from "@/shared/ui/card";
import { Slider } from "@/shared/ui/slider";
import { Toggle } from "@/shared/ui/toggle";
import { Skeleton } from "@/shared/ui/skeleton";
import { Search, SlidersHorizontal } from "lucide-react";

export function DynamicQueryPanel() {
  const { data: config, isLoading } = useAppConfig();

  if (isLoading) {
    return <DynamicQueryPanelSkeleton />;
  }

  if (!config) {
    return (
      <Card className='border-error bg-error/10'>
        <CardContent className='p-4 text-center text-errorForeground'>
          <p className='text-sm font-medium'>
            Failed to load system configuration.
          </p>
        </CardContent>
      </Card>
    );
  }

  const { hyperparameters } = config;

  return (
    <Card className='w-full'>
      <CardHeader className='flex flex-row items-center justify-between pb-2'>
        <div className='flex flex-col space-y-1'>
          <CardTitle className='flex items-center gap-2 text-lg'>
            <SlidersHorizontal className='h-5 w-5 text-primary' />
            Hyperparameters
          </CardTitle>
          <p className='text-sm text-muted-foreground'>
            Backend-controlled tuning.
          </p>
        </div>
      </CardHeader>
      <CardContent className='grid gap-6'>
        {/* Dynamic Sliders */}
        <div className='grid gap-4 md:grid-cols-2'>
          {/* Alpha Row */}
          <div className='space-y-3'>
            <div className='flex items-center justify-between'>
              <label className='text-sm font-medium leading-none text-foreground peer-disabled:cursor-not-allowed peer-disabled:opacity-70'>
                Alpha Weight
              </label>
              <span className='font-mono text-xs text-muted-foreground'>
                {hyperparameters.alpha.default}
              </span>
            </div>
            <Slider
              min={hyperparameters.alpha.min}
              max={hyperparameters.alpha.max}
              step={hyperparameters.alpha.step}
              defaultValue={[hyperparameters.alpha.default]}
            />
            <p className='text-xs text-muted-foreground'>
              {hyperparameters.alpha.description}
            </p>
          </div>

          {/* Beta Row */}
          <div className='space-y-3'>
            <div className='flex items-center justify-between'>
              <label className='text-sm font-medium leading-none text-foreground peer-disabled:cursor-not-allowed peer-disabled:opacity-70'>
                Beta (BM25)
              </label>
              <span className='font-mono text-xs text-muted-foreground'>
                {hyperparameters.beta.default}
              </span>
            </div>
            <Slider
              min={hyperparameters.beta.min}
              max={hyperparameters.beta.max}
              step={hyperparameters.beta.step}
              defaultValue={[hyperparameters.beta.default]}
            />
            <p className='text-xs text-muted-foreground'>
              {hyperparameters.beta.description}
            </p>
          </div>
        </div>

        {/* Dynamic Toggles */}
        <div className='grid gap-4 md:grid-cols-2'>
          {/* Hybrid Toggle */}
          <div className='flex flex-row items-center justify-between rounded-lg border border-border p-4 shadow-sm transition-colors hover:bg-surface'>
            <div className='space-y-0.5'>
              <label className='text-sm font-medium text-foreground'>
                Hybrid Search
              </label>
              <p className='text-xs text-muted-foreground'>
                {hyperparameters.hybrid.description}
              </p>
            </div>
            <Toggle defaultChecked={hyperparameters.hybrid.default} />
          </div>

          {/* Reranking Toggle */}
          <div className='flex flex-row items-center justify-between rounded-lg border border-border p-4 shadow-sm transition-colors hover:bg-surface'>
            <div className='space-y-0.5'>
              <label className='text-sm font-medium text-foreground'>
                Neural Reranking
              </label>
              <p className='text-xs text-muted-foreground'>
                {hyperparameters.reranking.description}
              </p>
            </div>
            <Toggle defaultChecked={hyperparameters.reranking.default} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function DynamicQueryPanelSkeleton() {
  return (
    <Card className='w-full'>
      <CardHeader className='flex flex-row items-center justify-between pb-2'>
        <div className='flex flex-col space-y-2'>
          <Skeleton className='h-6 w-32' />
          <Skeleton className='h-4 w-48' />
        </div>
      </CardHeader>
      <CardContent className='grid gap-6'>
        <div className='grid gap-4 md:grid-cols-2'>
          <div className='space-y-3'>
            <Skeleton className='h-4 w-full' />
            <Skeleton className='h-2 w-full' />
          </div>
          <div className='space-y-3'>
            <Skeleton className='h-4 w-full' />
            <Skeleton className='h-2 w-full' />
          </div>
        </div>
        <div className='grid gap-4 md:grid-cols-2'>
          <Skeleton className='h-16 w-full rounded-lg' />
          <Skeleton className='h-16 w-full rounded-lg' />
        </div>
      </CardContent>
    </Card>
  );
}
