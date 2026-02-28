"""
WHAT: Feature flags system for CortexDocs ∞.
WHY: Enables runtime toggling of system capabilities without code deployment.
     Supports A/B testing, gradual rollouts, and benchmark comparison by allowing
     individual pipeline stages to be enabled/disabled.
WHEN: Checked at service layer before executing optional pipeline stages.
WHERE: backend/app/core/features.py
HOW: Simple boolean flags loaded from environment. Checked via FeatureFlags singleton.
ALTERNATIVES CONSIDERED:
  - LaunchDarkly/Unleash: Overkill for local/single-instance deployment.
  - Database-backed flags: Adds DB dependency to feature checks — too tight coupling.
  - YAML config: Less ergonomic than env vars for container orchestration.
TRADEOFFS:
  - No gradual percentage rollout — acceptable for single-instance systems.
  - No audit trail of flag changes — mitigated by env var change tracking in deployment.
  - Restart required for flag changes — intentional for consistency within a request lifecycle.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class FeatureFlags(BaseSettings):
    """
    WHAT: Toggle switches for optional pipeline capabilities.
    WHY: Allows disabling expensive operations (reranking, contradiction detection)
         for performance benchmarking, debugging, or cost reduction.
    """

    # ─── Retrieval Features ────────────────────────────────────────
    ENABLE_HYBRID_SEARCH: bool = True
    """When disabled, falls back to vector-only retrieval."""

    ENABLE_RERANKING: bool = True
    """When disabled, skips cross-encoder reranking. Saves ~200ms per query."""

    ENABLE_ADAPTIVE_RETRIEVAL: bool = True
    """When disabled, uses fixed top_k regardless of confidence."""

    # ─── Intelligence Features ─────────────────────────────────────
    ENABLE_CONTRADICTION_DETECTION: bool = True
    """When disabled, skips numeric consistency checks across chunks."""

    ENABLE_INTENT_CLASSIFICATION: bool = True
    """When disabled, defaults to 'precise' mode for all queries."""

    ENABLE_CONFIDENCE_SCORING: bool = True
    """When disabled, returns a flat 0.0 confidence (unknown)."""

    # ─── Caching ───────────────────────────────────────────────────
    ENABLE_EMBEDDING_CACHE: bool = True
    """When disabled, recomputes embeddings for every query."""

    ENABLE_ANSWER_CACHE: bool = True
    """When disabled, never returns cached answers."""

    # ─── Observability ─────────────────────────────────────────────
    ENABLE_QUERY_LOGGING: bool = True
    """When disabled, skips writing query telemetry to DB."""

    ENABLE_LATENCY_TRACKING: bool = True
    """When disabled, skips per-stage latency measurement."""

    # ─── Security ──────────────────────────────────────────────────
    ENABLE_MAGIC_BYTES_VALIDATION: bool = True
    """When disabled, relies only on MIME type checking."""

    ENABLE_RATE_LIMITING: bool = True
    """When disabled, allows unlimited requests per IP."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "FF_",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_feature_flags() -> FeatureFlags:
    """
    WHAT: Singleton factory for FeatureFlags.
    WHY: Ensures consistent flag state across the application lifecycle.
    """
    return FeatureFlags()
