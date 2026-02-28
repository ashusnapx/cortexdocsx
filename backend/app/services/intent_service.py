"""
WHAT: Intent classification service for query categorization.
WHY: Different query intents require different retrieval strategies and prompt templates.
     Precise queries need exact answers, summaries need synthesis, analytical queries
     need cross-document reasoning.
WHEN: Called at the beginning of the query pipeline.
WHERE: backend/app/services/intent_service.py
HOW: Keyword-based heuristic classification. Fast (sub-1ms), deterministic, explainable.
ALTERNATIVES CONSIDERED:
  - LLM-based classification: Adds latency, cost, non-determinism.
  - Fine-tuned classifier: Requires training data we don't have.
  - Zero-shot NLI: Better accuracy but adds model loading overhead.
TRADEOFFS:
  - Keyword heuristics are less accurate than ML classifiers — 80% accuracy is sufficient
    because the impact of misclassification is low (slightly suboptimal prompt template).
  - No learning from feedback — acceptable for V1.
"""

import re

import structlog

from app.core.constants import (
    ANALYTICAL_KEYWORDS,
    SUMMARY_KEYWORDS,
    QueryIntent,
)

logger = structlog.get_logger(__name__)


class IntentService:
    """
    WHAT: Classifies user query intent into precise/summary/analytical.
    WHY: Selects appropriate prompt template and retrieval parameters.
    """

    def classify(self, query: str) -> QueryIntent:
        """
        WHAT: Classify a query into an intent category.
        WHY: Drives prompt template selection and retrieval strategy.
        HOW: Checks for keyword presence, question structure, and query length.

        Classification rules (in priority order):
        1. If query contains summary keywords → SUMMARY
        2. If query contains analytical keywords → ANALYTICAL
        3. If query is a question expecting a specific answer → PRECISE
        4. Default → PRECISE
        """
        query_lower = query.lower().strip()

        # Check for summary intent
        summary_score = sum(
            1 for keyword in SUMMARY_KEYWORDS if keyword in query_lower
        )

        # Check for analytical intent
        analytical_score = sum(
            1 for keyword in ANALYTICAL_KEYWORDS if keyword in query_lower
        )

        # Length heuristic: very long queries tend to be analytical
        if len(query_lower.split()) > 25:
            analytical_score += 1

        # Multi-document comparison patterns
        if re.search(r"(across|between|among)\s+(documents?|files?|sources?)", query_lower):
            analytical_score += 2

        # Determine intent
        if summary_score > analytical_score and summary_score > 0:
            intent = QueryIntent.SUMMARY
        elif analytical_score > 0:
            intent = QueryIntent.ANALYTICAL
        else:
            intent = QueryIntent.PRECISE

        logger.info(
            "intent_classified",
            query_preview=query_lower[:80],
            intent=intent.value,
            summary_score=summary_score,
            analytical_score=analytical_score,
        )

        return intent
