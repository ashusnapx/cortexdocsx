"""
WHAT: Global exception handler and error response middleware.
WHY: Ensures all errors return a consistent structured envelope regardless of
     where they originate. Prevents stack traces from leaking to clients.
WHEN: Catches all unhandled exceptions from route handlers.
WHERE: backend/app/middleware/error_handler.py
HOW: FastAPI exception handlers for HTTPException, validation errors, and catch-all.
ALTERNATIVES CONSIDERED:
  - Per-route try/except: Duplicative, error-prone, inconsistent formatting.
  - Starlette ExceptionMiddleware: Less integration with FastAPI's exception system.
TRADEOFFS:
  - Catch-all handler may mask bugs in development — mitigated by structured logging
    of full exception details before returning sanitized response.
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.constants import ErrorCode

logger = structlog.get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """
    WHAT: Registers global exception handlers on the FastAPI app.
    WHY: Called once during app initialization.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handles FastAPI/Starlette HTTP exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "http_exception",
            status_code=exc.status_code,
            detail=exc.detail,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "request_id": request_id,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handles Pydantic validation errors from request parsing."""
        request_id = getattr(request.state, "request_id", "unknown")
        errors = exc.errors()
        logger.warning(
            "validation_error",
            errors=errors,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "Request validation failed",
                    "details": errors,
                    "request_id": request_id,
                },
            },
        )

    @app.exception_handler(Exception)
    async def catch_all_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        WHAT: Catch-all for unhandled exceptions.
        WHY: Prevents raw stack traces from reaching clients.
        HOW: Logs full exception, returns sanitized 500 response.
        """
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(
            "unhandled_exception",
            error_type=type(exc).__name__,
            error_message=str(exc),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred. Check logs for details.",
                    "request_id": request_id,
                },
            },
        )
