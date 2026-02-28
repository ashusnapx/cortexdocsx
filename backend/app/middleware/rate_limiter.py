"""
WHAT: Per-IP rate limiting middleware for API protection.
WHY: Prevents abuse, ensures fair access, shows API maturity.
     Configurable window and request limits from Settings.
WHEN: Runs on every incoming request before route handlers.
WHERE: backend/app/middleware/rate_limiter.py
HOW: In-memory sliding window counter per IP address. Adds rate limit headers.
ALTERNATIVES CONSIDERED:
  - Redis-backed rate limiting: More robust for distributed systems, but adds dependency.
  - slowapi: Good library but adds dependency; our needs are simple enough for custom impl.
  - Token bucket: More sophisticated but unnecessary for single-instance deployment.
TRADEOFFS:
  - In-memory counter resets on restart — acceptable for local/single-instance.
  - No distributed coordination — would need Redis for multi-instance deployment.
  - Memory grows with unique IPs — mitigated by periodic cleanup.
"""

import time
from collections import defaultdict
from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import get_settings
from app.core.constants import ErrorCode
from app.core.features import get_feature_flags

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    WHAT: Sliding window rate limiter per client IP.
    WHY: Prevents API abuse. Adds standard rate limit response headers.
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup: float = time.time()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        flags = get_feature_flags()
        if not flags.ENABLE_RATE_LIMITING:
            return await call_next(request)

        settings = get_settings()
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path.endswith("/health"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        max_requests = settings.RATE_LIMIT_REQUESTS

        # Periodic cleanup of expired entries (every 60s)
        if now - self._last_cleanup > 60:
            self._cleanup(now, window)
            self._last_cleanup = now

        # Filter to requests within the current window
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip] if now - ts < window
        ]

        current_count = len(self._requests[client_ip])

        if current_count >= max_requests:
            retry_after = int(window - (now - self._requests[client_ip][0]))
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                count=current_count,
                limit=max_requests,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": ErrorCode.RATE_LIMITED.value,
                        "message": f"Rate limit exceeded. Try again in {retry_after}s.",
                    },
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                },
            )

        # Record this request
        self._requests[client_ip].append(now)

        response = await call_next(request)

        # Add rate limit headers to response
        remaining = max_requests - len(self._requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(now + window))

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For for proxied requests."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup(self, now: float, window: float) -> None:
        """Remove expired entries to prevent memory growth."""
        expired_ips = []
        for ip, timestamps in self._requests.items():
            self._requests[ip] = [ts for ts in timestamps if now - ts < window]
            if not self._requests[ip]:
                expired_ips.append(ip)
        for ip in expired_ips:
            del self._requests[ip]
