"""
WHAT: Common Pydantic v2 schemas for API response envelopes and shared types.
WHY: Consistent response structure across all endpoints. Every response uses
     the same envelope: {success, data, error}. Enables predictable frontend parsing.
WHEN: Used by all API route handlers for response serialization.
WHERE: backend/app/schemas/common.py
HOW: Generic TypeVar-based envelope for type-safe data field.
ALTERNATIVES CONSIDERED:
  - Dict responses: No validation, no documentation, no type safety.
  - Django REST Framework serializers: Not applicable to FastAPI.
TRADEOFFS:
  - Generic envelope adds minor serialization overhead — negligible vs. network latency.
  - Requires wrapping all responses — enforced by convention, not compiler.
"""

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """
    WHAT: Structured error information for API responses.
    WHY: Machine-readable error classification with human-readable messages.
    """
    code: str = Field(..., description="Machine-readable error code from ErrorCode enum")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[object] = Field(default=None, description="Additional error context")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracing")


class ApiResponse(BaseModel, Generic[T]):
    """
    WHAT: Standard API response envelope.
    WHY: Every endpoint returns this structure for predictable frontend handling.
    """
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        return cls(success=True, data=data)

    @classmethod
    def fail(
        cls,
        code: str,
        message: str,
        details: Optional[object] = None,
        request_id: Optional[str] = None,
    ) -> "ApiResponse":
        return cls(
            success=False,
            error=ErrorDetail(
                code=code,
                message=message,
                details=details,
                request_id=request_id,
            ),
        )


class PaginationMeta(BaseModel):
    """Pagination metadata for list endpoints."""
    total: int
    page: int
    per_page: int
    total_pages: int


class TimingStage(BaseModel):
    """A single pipeline stage timing entry for transparency UI."""
    stage: str
    duration_ms: float
    metadata: dict = Field(default_factory=dict)


class PipelineTiming(BaseModel):
    """Full pipeline timing breakdown."""
    stages: list[TimingStage] = Field(default_factory=list)
    total_ms: float = 0.0
