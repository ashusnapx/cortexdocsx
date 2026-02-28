"""
WHAT: Application-wide constants that are NOT environment-dependent.
WHY: Separates truly fixed values (error codes, status enums, magic bytes)
     from environment-configurable settings (config.py). Prevents duplication
     and ensures consistent usage across all layers.
WHEN: Imported at module level by any component needing constant values.
WHERE: backend/app/core/constants.py
HOW: Simple module-level constants. Enums for finite sets. Frozen dataclasses where grouping helps.
ALTERNATIVES CONSIDERED:
  - Putting everything in config.py: Conflates env-driven vs fixed values.
  - Django-style settings: Not idiomatic for FastAPI.
TRADEOFFS:
  - Constants file can grow large — mitigated by clear section grouping.
  - No runtime override — intentional; these values should never change per-environment.
"""

from enum import Enum


# ─── Ingestion Status ─────────────────────────────────────────────
class IngestionStatus(str, Enum):
    """
    WHAT: Lifecycle states for a document ingestion job.
    WHY: Typed enum prevents typo-based bugs in status checks.
    """
    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Query Intent ─────────────────────────────────────────────────
class QueryIntent(str, Enum):
    """
    WHAT: Classified intent modes for user queries.
    WHY: Different intents trigger different retrieval strategies and prompt templates.
    """
    PRECISE = "precise"
    SUMMARY = "summary"
    ANALYTICAL = "analytical"


# ─── Circuit Breaker State ────────────────────────────────────────
class CircuitBreakerState(str, Enum):
    """
    WHAT: State machine for the LLM circuit breaker.
    WHY: Exposes resilience state to monitoring and UI.
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ─── Index Health ─────────────────────────────────────────────────
class IndexHealth(str, Enum):
    """
    WHAT: Health states for the vector/BM25 indexes.
    WHY: Supports retrieval drift detection and stale index warnings.
    """
    HEALTHY = "healthy"
    STALE = "stale"
    REBUILDING = "rebuilding"
    UNAVAILABLE = "unavailable"


# ─── Error Codes ──────────────────────────────────────────────────
class ErrorCode(str, Enum):
    """
    WHAT: Structured error codes for the API response envelope.
    WHY: Machine-readable error classification for frontend error handling.
         Avoids relying on string-matching error messages.
    """
    # File errors
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_MIME_TYPE = "INVALID_MIME_TYPE"
    CORRUPT_FILE = "CORRUPT_FILE"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PAGE_LIMIT_EXCEEDED = "PAGE_LIMIT_EXCEEDED"

    # Database errors
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"

    # Vector store errors
    VECTOR_STORE_LOAD_FAILED = "VECTOR_STORE_LOAD_FAILED"
    VECTOR_STORE_SEARCH_FAILED = "VECTOR_STORE_SEARCH_FAILED"
    INDEX_STALE = "INDEX_STALE"

    # Embedding errors
    EMBEDDING_MODEL_LOAD_FAILED = "EMBEDDING_MODEL_LOAD_FAILED"
    EMBEDDING_GENERATION_FAILED = "EMBEDDING_GENERATION_FAILED"

    # LLM errors
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    LLM_CIRCUIT_OPEN = "LLM_CIRCUIT_OPEN"

    # Retrieval errors
    NO_RELEVANT_CHUNKS = "NO_RELEVANT_CHUNKS"
    PARTIAL_RETRIEVAL = "PARTIAL_RETRIEVAL"
    RETRIEVAL_FAILED = "RETRIEVAL_FAILED"

    # Ingestion errors
    INGESTION_FAILED = "INGESTION_FAILED"
    INGESTION_IN_PROGRESS = "INGESTION_IN_PROGRESS"

    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"

    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


# ─── PDF Magic Bytes ──────────────────────────────────────────────
PDF_MAGIC_BYTES = b"%PDF"
PDF_MAGIC_BYTES_OFFSET = 0
PDF_MAGIC_BYTES_LENGTH = 4

# ─── Scoring Constants ────────────────────────────────────────────
MIN_CONFIDENCE_SCORE = 0.0
MAX_CONFIDENCE_SCORE = 1.0
CONTRADICTION_NUMERIC_TOLERANCE = 0.05

# ─── Retrieval Constants ──────────────────────────────────────────
BM25_SCORE_NORMALIZATION_FACTOR = 10.0
VECTOR_SCORE_MIN_THRESHOLD = 0.0
DEFAULT_RETRIEVAL_TOP_K = 20

# ─── Token Estimation ─────────────────────────────────────────────
CHARS_PER_TOKEN_ESTIMATE = 4.0

# ─── Prompt Templates ─────────────────────────────────────────────
SYSTEM_PROMPT_PRECISE = """You are a precise information retrieval assistant.
Answer the question based ONLY on the provided context.
If the context does not contain the answer, say so explicitly.
Cite the source document and page number for every claim.
Be concise and factual."""

SYSTEM_PROMPT_SUMMARY = """You are a document summarization assistant.
Synthesize the key points from the provided context into a coherent summary.
Cover all major themes without unnecessary repetition.
Cite source documents and page numbers."""

SYSTEM_PROMPT_ANALYTICAL = """You are an analytical research assistant.
Analyze the provided context to answer the question.
Identify patterns, compare perspectives across documents, and note any contradictions.
Provide a structured, well-reasoned response with citations."""

INTENT_PROMPT_TEMPLATES = {
    "precise": SYSTEM_PROMPT_PRECISE,
    "summary": SYSTEM_PROMPT_SUMMARY,
    "analytical": SYSTEM_PROMPT_ANALYTICAL,
}

# ─── Intent Classification Keywords ───────────────────────────────
SUMMARY_KEYWORDS = frozenset({
    "summarize", "summary", "overview", "brief", "gist",
    "main points", "key takeaways", "highlights", "outline",
    "recap", "digest", "abstract",
})

ANALYTICAL_KEYWORDS = frozenset({
    "analyze", "compare", "contrast", "evaluate", "assess",
    "implications", "relationship", "correlate", "trend",
    "impact", "why", "how does", "what causes", "significance",
    "difference between", "pros and cons",
})

# ─── Numerical Entity Patterns (for contradiction detection) ──────
NUMERICAL_PATTERN = r"(\d+(?:\.\d+)?)\s*(%|percent|dollars?|USD|EUR|million|billion|thousand|kg|lb|miles?|km|hours?|minutes?|seconds?|years?|months?|days?|units?)"

# ─── Health Check Constants ───────────────────────────────────────
HEALTH_CHECK_DB_TIMEOUT = 5
HEALTH_CHECK_QUERY = "SELECT 1"
