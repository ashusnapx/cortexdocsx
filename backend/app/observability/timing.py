"""
WHAT: Latency measurement utilities for pipeline stage observability.
WHY: Every pipeline stage (parsing, chunking, embedding, retrieval, reranking, LLM)
     must report its latency for transparency UI and performance debugging.
WHEN: Used as async context manager or decorator around pipeline stages.
WHERE: backend/app/observability/timing.py
HOW: perf_counter for high-resolution timing. Results logged and returned for UI.
ALTERNATIVES CONSIDERED:
  - OpenTelemetry spans: Heavier dependency, but we add stubs for future integration.
  - time.time(): Lower resolution than perf_counter on some platforms.
TRADEOFFS:
  - perf_counter measures wall-clock time, not CPU time — appropriate for I/O-bound stages.
  - Timing overhead is ~1μs per measurement — negligible.
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TimingResult:
    """
    WHAT: Container for a single stage's timing measurement.
    WHY: Typed result enables structured logging and UI serialization.
    """
    stage: str
    duration_ms: float
    metadata: dict = field(default_factory=dict)


@dataclass
class PipelineTimer:
    """
    WHAT: Accumulates timing results across multiple pipeline stages.
    WHY: Provides a unified view of the full pipeline's performance.
    """
    stages: list[TimingResult] = field(default_factory=list)
    _start_time: Optional[float] = field(default=None, repr=False)

    def start(self) -> None:
        self._start_time = time.perf_counter()

    @property
    def total_ms(self) -> float:
        return sum(s.duration_ms for s in self.stages)

    def add_stage(self, stage: str, duration_ms: float, **metadata: object) -> TimingResult:
        result = TimingResult(stage=stage, duration_ms=round(duration_ms, 2), metadata=metadata)
        self.stages.append(result)
        return result

    def to_dict(self) -> dict:
        return {
            "stages": [
                {"stage": s.stage, "duration_ms": s.duration_ms, "metadata": s.metadata}
                for s in self.stages
            ],
            "total_ms": round(self.total_ms, 2),
        }


@asynccontextmanager
async def timed_stage(
    timer: PipelineTimer, stage_name: str, **metadata: object
) -> AsyncGenerator[dict, None]:
    """
    WHAT: Async context manager that measures a pipeline stage's duration.
    WHY: Clean syntax for wrapping any async operation with timing.
    HOW: Records start time on entry, calculates duration on exit, adds to timer.

    Usage:
        timer = PipelineTimer()
        async with timed_stage(timer, "embedding") as ctx:
            embeddings = await model.encode(texts)
            ctx["count"] = len(embeddings)
    """
    ctx: dict = {}
    start = time.perf_counter()
    try:
        yield ctx
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        all_metadata = {**metadata, **ctx}
        result = timer.add_stage(stage_name, duration_ms, **all_metadata)
        logger.info(
            "pipeline_stage_completed",
            stage=result.stage,
            duration_ms=result.duration_ms,
            **all_metadata,
        )
