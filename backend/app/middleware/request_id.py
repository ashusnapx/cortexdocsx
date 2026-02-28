"""
WHAT: Request ID middleware for distributed tracing and log correlation.
WHY: Every request gets a unique ID that propagates through all log entries,
     DB queries, and response headers. Essential for debugging in production.
WHEN: Runs on every incoming HTTP request as ASGI middleware.
WHERE: backend/app/middleware/request_id.py
HOW: Checks X-Request-ID header (or generates UUID4), binds to structlog contextvars.
ALTERNATIVES CONSIDERED:
  - Starlette middleware class: Less control over ASGI lifecycle.
  - OpenTelemetry trace ID: Would work but adds heavy dependency for this single feature.
TRADEOFFS:
  - UUID4 generation adds ~2μs per request — negligible.
  - Contextvars binding is thread-safe but requires async-aware structlog processors.
"""

import uuid
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    WHAT: Injects X-Request-ID into every request and response.
    WHY: Enables end-to-end request tracing across logs, DB, and responses.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind to structlog context so all log entries in this request include the ID
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Store on request state for access in route handlers
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
