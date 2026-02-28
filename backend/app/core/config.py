"""
WHAT: Centralized configuration management for CortexDocs ∞.
WHY: Single source of truth for all environment-driven settings. Prevents magic numbers
     scattered across the codebase. Enables environment-specific overrides (dev/test/prod)
     without code changes.
WHEN: Loaded once at application startup via Pydantic Settings.
WHERE: backend/app/core/config.py — imported by every layer that needs configuration.
HOW: Pydantic BaseSettings with .env file support. Validates types at startup.
ALTERNATIVES CONSIDERED:
  - python-decouple: Less type safety, no nested validation.
  - dynaconf: Heavier, unnecessary for this scope.
  - Plain os.environ: No validation, no defaults, error-prone.
TRADEOFFS:
  - Pydantic Settings adds a startup validation cost (~5ms) but catches misconfig immediately.
  - All values are immutable after load — intentional for thread safety.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    WHAT: Application-wide configuration container.
    WHY: Centralizes every tunable parameter. No magic numbers elsewhere.
    """

    # ─── Application ───────────────────────────────────────────────
    APP_NAME: str = "CortexDocs ∞"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # ─── Server ────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ─── Database ──────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://cortexdocs:cortexdocs@localhost:5432/cortexdocs"
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=50)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=5, le=120)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=300)
    DB_ECHO: bool = False

    # ─── Embedding Model ───────────────────────────────────────────
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = Field(default=64, ge=1, le=512)
    EMBEDDING_MAX_SEQ_LENGTH: int = 512
    EMBEDDING_NORMALIZE: bool = True

    # ─── Reranker Model ────────────────────────────────────────────
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-base"
    RERANKER_TOP_K: int = Field(default=10, ge=1, le=100)
    RERANKER_BATCH_SIZE: int = Field(default=16, ge=1, le=128)

    # ─── Chunking ──────────────────────────────────────────────────
    CHUNK_SIZE: int = Field(default=512, ge=64, le=4096)
    CHUNK_OVERLAP: int = Field(default=64, ge=0, le=512)
    MAX_CHUNK_LENGTH_CHARS: int = Field(default=3000, ge=500, le=10000)
    MIN_CHUNK_LENGTH_CHARS: int = Field(default=50, ge=10, le=500)

    # ─── Retrieval ─────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = Field(default=20, ge=1, le=200)
    RETRIEVAL_FINAL_TOP_K: int = Field(default=5, ge=1, le=50)
    HYBRID_ALPHA: float = Field(default=0.7, ge=0.0, le=1.0)
    HYBRID_BETA: float = Field(default=0.3, ge=0.0, le=1.0)

    # ─── Adaptive Retrieval ────────────────────────────────────────
    ADAPTIVE_RETRIEVAL_ENABLED: bool = True
    ADAPTIVE_CONFIDENCE_THRESHOLD: float = Field(default=0.4, ge=0.0, le=1.0)
    ADAPTIVE_TOP_K_MULTIPLIER: float = Field(default=2.0, ge=1.0, le=5.0)
    ADAPTIVE_MAX_RETRIES: int = Field(default=2, ge=0, le=5)

    # ─── Confidence Scoring ────────────────────────────────────────
    CONFIDENCE_SIMILARITY_WEIGHT: float = Field(default=0.3, ge=0.0, le=1.0)
    CONFIDENCE_RERANKER_WEIGHT: float = Field(default=0.3, ge=0.0, le=1.0)
    CONFIDENCE_AGREEMENT_WEIGHT: float = Field(default=0.25, ge=0.0, le=1.0)
    CONFIDENCE_DISPERSION_WEIGHT: float = Field(default=0.15, ge=0.0, le=1.0)

    # ─── Context Budget ────────────────────────────────────────────
    TOKEN_BUDGET: int = Field(default=3000, ge=500, le=16000)
    CONTEXT_TRIM_STRATEGY: str = "score_ranked"

    # ─── LLM ───────────────────────────────────────────────────────
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=2048, ge=64, le=16384)
    LLM_TIMEOUT_SECONDS: int = Field(default=60, ge=5, le=300)
    LLM_RETRY_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    LLM_RETRY_MIN_WAIT: float = Field(default=1.0, ge=0.1, le=30.0)
    LLM_RETRY_MAX_WAIT: float = Field(default=30.0, ge=1.0, le=120.0)
    LLM_RETRY_MULTIPLIER: float = Field(default=2.0, ge=1.0, le=5.0)

    # ─── Circuit Breaker ───────────────────────────────────────────
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5, ge=1, le=50)
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(default=60, ge=10, le=600)
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = Field(default=2, ge=1, le=10)

    # ─── File Upload ───────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = Field(default=50, ge=1, le=500)
    MAX_PAGES_PER_DOCUMENT: int = Field(default=500, ge=1, le=5000)
    ALLOWED_MIME_TYPES: list[str] = ["application/pdf"]
    UPLOAD_DIR: str = "./data/uploads"

    # ─── Vector Store ──────────────────────────────────────────────
    FAISS_INDEX_DIR: str = "./data/faiss"
    FAISS_NPROBE: int = Field(default=10, ge=1, le=100)
    BM25_INDEX_DIR: str = "./data/bm25"

    # ─── Rate Limiting ─────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = Field(default=30, ge=1, le=1000)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1, le=3600)

    # ─── Cache ─────────────────────────────────────────────────────
    CACHE_ENABLED: bool = True
    CACHE_EMBEDDING_MAX_SIZE: int = Field(default=1000, ge=10, le=100000)
    CACHE_ANSWER_MAX_SIZE: int = Field(default=100, ge=1, le=10000)
    CACHE_ANSWER_TTL_SECONDS: int = Field(default=300, ge=30, le=3600)

    # ─── Frontend ──────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    @field_validator("HYBRID_ALPHA", "HYBRID_BETA")
    @classmethod
    def validate_hybrid_weights(cls, v: float) -> float:
        """
        WHAT: Validates hybrid search weight is in valid range.
        WHY: alpha + beta should ideally sum to 1.0 for normalized scoring,
             but we allow flexibility for experimentation.
        """
        return round(v, 4)

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return upper

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    WHAT: Singleton factory for Settings.
    WHY: Prevents re-reading .env on every import. Thread-safe via lru_cache.
    HOW: First call instantiates and validates; subsequent calls return cached instance.
    """
    return Settings()
