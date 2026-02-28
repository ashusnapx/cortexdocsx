"""
WHAT: Structured logging configuration for CortexDocs ∞.
WHY: JSON-formatted structured logs enable machine parsing, log aggregation,
     and correlation via request IDs. Human-readable in dev, JSON in production.
WHEN: Configured once at app startup. Logger instances created per-module.
WHERE: backend/app/observability/logging.py
HOW: Structlog with processor chain, bound to stdlib logging.
ALTERNATIVES CONSIDERED:
  - stdlib logging only: No structured fields, poor correlation.
  - Loguru: Nice API but less ecosystem support for structured JSON output.
  - Python-json-logger: Works but structlog's processor chain is more powerful.
TRADEOFFS:
  - Structlog adds ~1ms overhead per log call — negligible vs. I/O cost.
  - JSON logs are harder to read in terminal — mitigated by dev renderer.
"""

import logging
import sys

import structlog
from app.core.config import get_settings


def configure_logging() -> None:
    """
    WHAT: Configure structlog and stdlib logging for the application.
    WHY: Called once at startup. Sets up processor chain and output format.
    HOW: Dev mode uses console renderer; production uses JSON renderer.
    """
    settings = get_settings()
    is_dev = settings.ENVIRONMENT == "development"

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_dev:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(
            colors=True,
        )
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.LOG_LEVEL)

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.DB_ECHO else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
