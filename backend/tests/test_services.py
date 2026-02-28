"""
WHAT: Service layer tests with mocked dependencies.
WHY: Validates business logic in isolation from infrastructure.
     Mock LLM, vector store, and BM25 enable deterministic, fast tests.
WHEN: Run via pytest as part of the test suite.
WHERE: backend/tests/test_services.py
HOW: Uses mock fixtures from conftest.py injected into service constructors.
ALTERNATIVES CONSIDERED: Integration tests with real models — too slow for CI.
TRADEOFFS: Mocks don't catch integration bugs — complemented by manual testing.
"""

import pytest

from app.core.constants import QueryIntent
from app.services.chunking_service import ChunkingService
from app.services.confidence_service import ConfidenceService
from app.services.intent_service import IntentService


class TestChunkingService:
    """Tests for page-aware semantic chunking."""

    def test_basic_chunking(self):
        service = ChunkingService()
        pages = [
            {"page_number": 1, "text": "This is the first sentence. This is the second sentence. " * 20},
        ]
        chunks = service.chunk_pages(pages)
        assert len(chunks) > 0
        assert all(c.page_number == 1 for c in chunks)
        assert all(c.content for c in chunks)

    def test_empty_page_handling(self):
        service = ChunkingService()
        pages = [
            {"page_number": 1, "text": ""},
            {"page_number": 2, "text": "Some content here."},
        ]
        chunks = service.chunk_pages(pages)
        assert all(c.page_number == 2 for c in chunks)

    def test_multi_page_chunking(self):
        service = ChunkingService()
        pages = [
            {"page_number": i, "text": f"Content for page {i}. " * 30}
            for i in range(1, 4)
        ]
        chunks = service.chunk_pages(pages)
        assert len(chunks) > 0
        page_numbers = set(c.page_number for c in chunks)
        assert len(page_numbers) > 1

    def test_chunk_index_sequential(self):
        service = ChunkingService()
        pages = [
            {"page_number": 1, "text": "Sentence one. " * 50},
        ]
        chunks = service.chunk_pages(pages)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i


class TestIntentService:
    """Tests for query intent classification."""

    def test_precise_intent(self):
        service = IntentService()
        intent = service.classify("What is the revenue for Q3 2024?")
        assert intent == QueryIntent.PRECISE

    def test_summary_intent(self):
        service = IntentService()
        intent = service.classify("Summarize the main findings of the report")
        assert intent == QueryIntent.SUMMARY

    def test_analytical_intent(self):
        service = IntentService()
        intent = service.classify("Compare the performance metrics across documents")
        assert intent == QueryIntent.ANALYTICAL

    def test_default_to_precise(self):
        service = IntentService()
        intent = service.classify("hello")
        assert intent == QueryIntent.PRECISE


class TestConfidenceService:
    """Tests for confidence scoring and contradiction detection."""

    def test_empty_chunks_zero_confidence(self):
        service = ConfidenceService()
        confidence = service.compute_confidence([], "test query")
        assert confidence.overall == 0.0

    def test_high_score_chunks(self):
        service = ConfidenceService()
        chunks = [
            {"content": "relevant content", "final_score": 0.95, "reranker_score": 0.9},
            {"content": "relevant content too", "final_score": 0.90, "reranker_score": 0.85},
        ]
        confidence = service.compute_confidence(chunks, "test query")
        assert confidence.overall > 0.5

    def test_contradiction_detection(self):
        service = ConfidenceService()
        chunks = [
            {
                "content": "The revenue was 100 million in 2024.",
                "document_name": "Report A",
                "page_number": 1,
            },
            {
                "content": "The revenue reached 500 million in 2024.",
                "document_name": "Report B",
                "page_number": 3,
            },
        ]
        contradictions = service.detect_contradictions(chunks)
        assert len(contradictions) > 0

    def test_no_contradictions_same_values(self):
        service = ConfidenceService()
        chunks = [
            {
                "content": "The count was 100 units.",
                "document_name": "Doc A",
                "page_number": 1,
            },
            {
                "content": "The count was 100 units.",
                "document_name": "Doc B",
                "page_number": 2,
            },
        ]
        contradictions = service.detect_contradictions(chunks)
        # Same value, same unit — no contradiction
        assert len(contradictions) == 0
