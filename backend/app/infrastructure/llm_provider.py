"""
WHAT: LLM provider abstraction with mock implementation, retry logic, and circuit breaker.
WHY: Decouples the query pipeline from any specific LLM vendor. Mock provider enables
     full system testing without LLM costs. Circuit breaker prevents cascading failures.
WHEN: Used by QueryService for response generation.
WHERE: backend/app/infrastructure/llm_provider.py
HOW: Protocol-based abstraction with concrete MockLLMProvider and OpenAI-compatible provider.
     Tenacity for retry with exponential backoff. Manual circuit breaker state machine.
ALTERNATIVES CONSIDERED:
  - LangChain: Heavy abstraction, too many layers for a focused system.
  - LiteLLM: Good multi-provider support but adds dependency.
  - Direct httpx calls: Simpler but no retry/circuit logic.
TRADEOFFS:
  - Mock provider returns deterministic responses — great for testing, not for demos.
  - Circuit breaker is in-memory — resets on restart. Acceptable for single-instance.
  - Retry logic adds latency on failures — intentional for reliability.
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Optional, Protocol

import structlog

from app.core.config import get_settings
from app.core.constants import CircuitBreakerState

logger = structlog.get_logger(__name__)


class LLMProvider(Protocol):
    """
    WHAT: Protocol defining the LLM provider interface.
    WHY: Enables swapping providers without changing service code.
    """

    async def generate(
        self, prompt: str, system_prompt: str, max_tokens: int
    ) -> str: ...

    async def generate_stream(
        self, prompt: str, system_prompt: str, max_tokens: int
    ) -> AsyncGenerator[str, None]: ...

    async def health_check(self) -> dict: ...


class CircuitBreaker:
    """
    WHAT: Circuit breaker pattern implementation for LLM calls.
    WHY: Prevents repeated calls to a failing LLM service — fails fast
         after threshold and recovers gradually via half-open state.
    HOW: State machine: CLOSED → (failures) → OPEN → (timeout) → HALF_OPEN → (success) → CLOSED.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._failure_threshold = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self._recovery_timeout = settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
        self._half_open_max = settings.CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS
        self._failure_count = 0
        self._half_open_calls = 0
        self._state = CircuitBreakerState.CLOSED
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.OPEN:
            if self._last_failure_time and (
                time.time() - self._last_failure_time > self._recovery_timeout
            ):
                self._state = CircuitBreakerState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def record_success(self) -> None:
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self._half_open_max:
                self._state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                logger.info("circuit_breaker_closed", reason="half_open_success")
        elif self._state == CircuitBreakerState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.OPEN
            logger.warning("circuit_breaker_opened", reason="half_open_failure")
        elif self._failure_count >= self._failure_threshold:
            self._state = CircuitBreakerState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self._failure_count,
                threshold=self._failure_threshold,
            )

    def can_execute(self) -> bool:
        state = self.state
        if state == CircuitBreakerState.CLOSED:
            return True
        if state == CircuitBreakerState.HALF_OPEN:
            return self._half_open_calls < self._half_open_max
        return False

    def get_status(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout_seconds": self._recovery_timeout,
        }


class MockLLMProvider:
    """
    WHAT: Deterministic mock LLM provider for testing and development.
    WHY: Enables full system testing without LLM API costs or rate limits.
         Returns structured, predictable responses based on input context.
    """

    def __init__(self) -> None:
        self._circuit_breaker = CircuitBreaker()

    async def generate(
        self, prompt: str, system_prompt: str, max_tokens: int = 2048
    ) -> str:
        """Generate a deterministic response based on the prompt."""
        if not self._circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker is OPEN — LLM calls blocked")

        try:
            # Simulate realistic latency
            await asyncio.sleep(0.5)

            context_lines = [
                line.strip()
                for line in prompt.split("\n")
                if line.strip() and not line.strip().startswith("Question:")
            ]

            response = self._build_mock_response(prompt, context_lines)
            self._circuit_breaker.record_success()
            return response

        except Exception as e:
            self._circuit_breaker.record_failure()
            raise

    async def generate_stream(
        self, prompt: str, system_prompt: str, max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream a deterministic response token by token."""
        if not self._circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker is OPEN — LLM calls blocked")

        try:
            response = await self.generate(prompt, system_prompt, max_tokens)
            words = response.split()

            for i, word in enumerate(words):
                separator = " " if i > 0 else ""
                yield separator + word
                await asyncio.sleep(0.03)  # Simulate streaming latency

            self._circuit_breaker.record_success()

        except Exception as e:
            self._circuit_breaker.record_failure()
            raise

    async def health_check(self) -> dict:
        return {
            "provider": "mock",
            "status": "ok",
            "circuit_breaker": self._circuit_breaker.get_status(),
        }

    def _build_mock_response(self, prompt: str, context_lines: list[str]) -> str:
        """Build a structured mock response from context."""
        if not context_lines:
            return (
                "Based on the available documents, I could not find sufficient "
                "information to answer this question with confidence. The retrieved "
                "context did not contain relevant passages."
            )

        # Extract meaningful content snippets
        snippets = []
        for line in context_lines[:5]:
            if len(line) > 20 and not line.startswith("["):
                snippets.append(line[:200])

        if not snippets:
            snippets = ["The provided documents contain relevant information."]

        response_parts = [
            "Based on the analysis of the provided documents, here are the key findings:\n",
        ]

        for i, snippet in enumerate(snippets[:3], 1):
            response_parts.append(f"{i}. {snippet}\n")

        response_parts.append(
            "\nThis response is generated by the CortexDocs ∞ mock LLM provider. "
            "Configure a real LLM provider (OpenAI, Anthropic) via LLM_PROVIDER and "
            "LLM_API_KEY environment variables for production responses."
        )

        return "\n".join(response_parts)

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker


class OpenAICompatibleProvider:
    """
    WHAT: OpenAI-compatible LLM provider with retry and circuit breaker.
    WHY: Production provider for real LLM responses. Works with any
         OpenAI API-compatible endpoint (OpenAI, Azure, local vllm, etc.).
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._circuit_breaker = CircuitBreaker()

    async def generate(
        self, prompt: str, system_prompt: str, max_tokens: int = 2048
    ) -> str:
        """Generate a response using an OpenAI-compatible API."""
        if not self._circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker is OPEN — LLM calls blocked")

        import httpx
        from tenacity import (
            retry,
            retry_if_exception_type,
            stop_after_attempt,
            wait_exponential,
        )

        @retry(
            stop=stop_after_attempt(self._settings.LLM_RETRY_MAX_ATTEMPTS),
            wait=wait_exponential(
                multiplier=self._settings.LLM_RETRY_MULTIPLIER,
                min=self._settings.LLM_RETRY_MIN_WAIT,
                max=self._settings.LLM_RETRY_MAX_WAIT,
            ),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        )
        async def _call_api() -> str:
            async with httpx.AsyncClient(
                timeout=self._settings.LLM_TIMEOUT_SECONDS
            ) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._settings.LLM_MODEL_NAME,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": self._settings.LLM_TEMPERATURE,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        try:
            result = await _call_api()
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            self._circuit_breaker.record_failure()
            raise

    async def generate_stream(
        self, prompt: str, system_prompt: str, max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI-compatible API."""
        if not self._circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker is OPEN — LLM calls blocked")

        import httpx

        try:
            async with httpx.AsyncClient(
                timeout=self._settings.LLM_TIMEOUT_SECONDS
            ) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._settings.LLM_MODEL_NAME,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": self._settings.LLM_TEMPERATURE,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            import json
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue

            self._circuit_breaker.record_success()
        except Exception as e:
            self._circuit_breaker.record_failure()
            raise

    async def health_check(self) -> dict:
        return {
            "provider": "openai_compatible",
            "status": "ok" if self._settings.LLM_API_KEY else "no_api_key",
            "model": self._settings.LLM_MODEL_NAME,
            "circuit_breaker": self._circuit_breaker.get_status(),
        }

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker


class GeminiProvider:
    """
    WHAT: Google Gemini LLM provider with retry and circuit breaker.
    WHY: Handles native integration with gemini-2.5-flash-lite via google-genai SDK.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._circuit_breaker = CircuitBreaker()
        import os
        from google import genai
        # Initialize the synchronous underlying client. 
        # For true async in google-genai you use client.aio
        self._client = genai.Client(api_key=self._settings.LLM_API_KEY)

    async def generate(
        self, prompt: str, system_prompt: str, max_tokens: int = 2048
    ) -> str:
        """Generate a response using Google GenAI."""
        if not self._circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker is OPEN — LLM calls blocked")

        import httpx
        from tenacity import (
            retry,
            retry_if_exception_type,
            stop_after_attempt,
            wait_exponential,
        )
        from google.genai.errors import APIError

        @retry(
            stop=stop_after_attempt(self._settings.LLM_RETRY_MAX_ATTEMPTS),
            wait=wait_exponential(
                multiplier=self._settings.LLM_RETRY_MULTIPLIER,
                min=self._settings.LLM_RETRY_MIN_WAIT,
                max=self._settings.LLM_RETRY_MAX_WAIT,
            ),
            retry=retry_if_exception_type((httpx.TimeoutException, APIError)),
        )
        async def _call_api() -> str:
            response = await self._client.aio.models.generate_content(
                model=self._settings.LLM_MODEL_NAME,
                contents=prompt,
                config={
                    "system_instruction": system_prompt,
                    "max_output_tokens": max_tokens,
                    "temperature": self._settings.LLM_TEMPERATURE,
                },
            )
            return response.text

        try:
            result = await _call_api()
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            self._circuit_breaker.record_failure()
            raise

    async def generate_stream(
        self, prompt: str, system_prompt: str, max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream response from Google GenAI API."""
        if not self._circuit_breaker.can_execute():
            raise RuntimeError("Circuit breaker is OPEN — LLM calls blocked")

        try:
            response_stream = await self._client.aio.models.generate_content_stream(
                model=self._settings.LLM_MODEL_NAME,
                contents=prompt,
                config={
                    "system_instruction": system_prompt,
                    "max_output_tokens": max_tokens,
                    "temperature": self._settings.LLM_TEMPERATURE,
                },
            )
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text

            self._circuit_breaker.record_success()
        except Exception as e:
            self._circuit_breaker.record_failure()
            raise

    async def health_check(self) -> dict:
        return {
            "provider": "gemini",
            "status": "ok" if self._settings.LLM_API_KEY else "no_api_key",
            "model": self._settings.LLM_MODEL_NAME,
            "circuit_breaker": self._circuit_breaker.get_status(),
        }

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker


def create_llm_provider() -> MockLLMProvider | OpenAICompatibleProvider | GeminiProvider:
    """
    WHAT: Factory function for creating the configured LLM provider.
    WHY: Reads LLM_PROVIDER from settings to determine which implementation.
    """
    settings = get_settings()
    if settings.LLM_PROVIDER == "openai":
        logger.info("llm_provider_created", provider="openai_compatible")
        return OpenAICompatibleProvider()
    elif settings.LLM_PROVIDER == "gemini":
        logger.info("llm_provider_created", provider="gemini")
        return GeminiProvider()
    else:
        logger.info("llm_provider_created", provider="mock")
        return MockLLMProvider()
