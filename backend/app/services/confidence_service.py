"""
WHAT: Confidence scoring and contradiction detection engine.
WHY: Quantifies retrieval quality and flags inconsistencies across documents.
     Confidence score gives users calibrated trust signals. Contradiction detection
     prevents the system from presenting conflicting information without warning.
WHEN: Called after retrieval and reranking, before LLM generation.
WHERE: backend/app/services/confidence_service.py
HOW: Weighted combination of similarity, reranker, agreement, and dispersion signals.
     Numerical entity extraction and comparison for contradiction detection.
ALTERNATIVES CONSIDERED:
  - LLM-based confidence: Circular — LLM judging its own confidence.
  - Calibrated uncertainty: Requires extensive training data.
  - Simple threshold: Too binary — percentage gives more information.
TRADEOFFS:
  - Heuristic confidence is not statistically calibrated — honest approximation.
  - Contradiction detection limited to numerical entities — full semantic contradiction
    detection would require NLI models (future enhancement).
  - Weights are manually tuned — could be learned from feedback data.
"""

import re
from typing import Optional

import numpy as np
import structlog

from app.core.config import get_settings
from app.core.constants import (
    CONTRADICTION_NUMERIC_TOLERANCE,
    MAX_CONFIDENCE_SCORE,
    MIN_CONFIDENCE_SCORE,
    NUMERICAL_PATTERN,
)
from app.schemas.query import ConfidenceBreakdown, Contradiction

logger = structlog.get_logger(__name__)


class ConfidenceService:
    """
    WHAT: Computes confidence scores and detects contradictions.
    WHY: Trust calibration and consistency checking across retrieved chunks.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def compute_confidence(
        self,
        chunks: list[dict],
        query: str,
    ) -> ConfidenceBreakdown:
        """
        WHAT: Compute a weighted confidence score from retrieval signals.
        WHY: Gives users a quantified trust level for the response.

        Components:
        1. Similarity mean — How well do chunks match the query?
        2. Reranker score — How does the cross-encoder rate relevance?
        3. Agreement — How consistent are the top chunks with each other?
        4. Dispersion — How spread are the scores? (tight = confident)
        """
        if not chunks:
            return ConfidenceBreakdown(
                overall=0.0,
                similarity_component=0.0,
                reranker_component=0.0,
                agreement_component=0.0,
                dispersion_component=0.0,
            )

        # 1. Similarity component (mean of final scores)
        scores = [c.get("final_score", c.get("combined_score", 0.0)) for c in chunks]
        similarity_mean = float(np.mean(scores)) if scores else 0.0
        similarity_component = min(1.0, max(0.0, similarity_mean))

        # 2. Reranker component (mean of reranker scores if available)
        reranker_scores = [c.get("reranker_score", 0.0) for c in chunks if c.get("reranker_score")]
        reranker_component = float(np.mean(reranker_scores)) if reranker_scores else 0.5

        # 3. Agreement component — measure content overlap between top chunks
        agreement_component = self._compute_agreement(chunks)

        # 4. Dispersion component — low variance = high confidence
        if len(scores) > 1:
            score_std = float(np.std(scores))
            # Inverse of dispersion: low std → high confidence
            dispersion_component = max(0.0, 1.0 - score_std * 2)
        else:
            dispersion_component = 0.5

        # Weighted combination
        w = self._settings
        overall = (
            w.CONFIDENCE_SIMILARITY_WEIGHT * similarity_component
            + w.CONFIDENCE_RERANKER_WEIGHT * reranker_component
            + w.CONFIDENCE_AGREEMENT_WEIGHT * agreement_component
            + w.CONFIDENCE_DISPERSION_WEIGHT * dispersion_component
        )

        overall = float(np.clip(overall, MIN_CONFIDENCE_SCORE, MAX_CONFIDENCE_SCORE))

        breakdown = ConfidenceBreakdown(
            overall=round(overall, 4),
            similarity_component=round(similarity_component, 4),
            reranker_component=round(reranker_component, 4),
            agreement_component=round(agreement_component, 4),
            dispersion_component=round(dispersion_component, 4),
        )

        logger.info(
            "confidence_computed",
            overall=breakdown.overall,
            components={
                "similarity": breakdown.similarity_component,
                "reranker": breakdown.reranker_component,
                "agreement": breakdown.agreement_component,
                "dispersion": breakdown.dispersion_component,
            },
        )

        return breakdown

    def detect_contradictions(self, chunks: list[dict]) -> list[Contradiction]:
        """
        WHAT: Detect numerical contradictions across retrieved chunks.
        WHY: When chunks from different documents present conflicting data,
             the user must be warned before trusting the response.
        HOW: Extract numerical entities with units, compare values across chunks,
             flag significant discrepancies.
        """
        contradictions: list[Contradiction] = []
        entities: dict[str, list[tuple[float, str, str]]] = {}

        for chunk in chunks:
            content = chunk.get("content", "")
            source = chunk.get("document_name", "Unknown")
            page = chunk.get("page_number", 0)
            source_label = f"{source} (p.{page})"

            matches = re.finditer(NUMERICAL_PATTERN, content, re.IGNORECASE)
            for match in matches:
                value = float(match.group(1))
                unit = match.group(2).lower().strip()
                key = unit

                if key not in entities:
                    entities[key] = []
                entities[key].append((value, source_label, match.group(0)))

        # Compare values within same unit group
        for unit, values in entities.items():
            if len(values) < 2:
                continue

            for i in range(len(values)):
                for j in range(i + 1, len(values)):
                    val_a, src_a, raw_a = values[i]
                    val_b, src_b, raw_b = values[j]

                    # Same source — not a contradiction
                    if src_a == src_b:
                        continue

                    # Check if values differ significantly
                    if val_a == 0 and val_b == 0:
                        continue

                    max_val = max(abs(val_a), abs(val_b))
                    if max_val > 0:
                        relative_diff = abs(val_a - val_b) / max_val
                    else:
                        relative_diff = 0.0

                    if relative_diff > CONTRADICTION_NUMERIC_TOLERANCE:
                        severity = "warning" if relative_diff < 0.5 else "critical"
                        contradictions.append(Contradiction(
                            entity=unit,
                            value_a=raw_a,
                            source_a=src_a,
                            value_b=raw_b,
                            source_b=src_b,
                            severity=severity,
                        ))

        if contradictions:
            logger.warning(
                "contradictions_detected",
                count=len(contradictions),
                entities=[c.entity for c in contradictions],
            )

        return contradictions

    def _compute_agreement(self, chunks: list[dict]) -> float:
        """
        WHAT: Measure content agreement between top chunks.
        WHY: If chunks contain similar vocabulary, they likely agree on the topic.
        HOW: Jaccard similarity of tokenized content between all pairs.
        """
        if len(chunks) < 2:
            return 0.5

        contents = [set(c.get("content", "").lower().split()) for c in chunks[:5]]
        similarities: list[float] = []

        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                intersection = contents[i] & contents[j]
                union = contents[i] | contents[j]
                if union:
                    similarities.append(len(intersection) / len(union))

        return float(np.mean(similarities)) if similarities else 0.5
