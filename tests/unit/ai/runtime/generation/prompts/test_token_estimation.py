"""
Unit tests for TokenCounter's local, network-free token estimation.

Token estimation moved off PromptService and onto TokenCounter
(app/ai/runtime/generation/observability/token_counter.py). Only the
approximate/local path is exercised here, via GenerationProvider.OLLAMA
-- OpenAI/Groq also resolve locally through tiktoken, but Claude/Gemini
dial out to live APIs and have no place in a deterministic unit test.
The Anthropic/Gemini SDK clients are mocked out so TokenCounter can be
constructed without real API keys.

Covers:
- Empty text estimates to a non-zero floor (the fallback never claims
  zero tokens)
- A large prompt scales with word count
- The same input always produces the same estimate (no hidden state)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.observability.token_counter import TokenCounter


def _make_token_counter() -> TokenCounter:
    with (
        patch(
            "app.ai.runtime.generation.observability.token_counter.AsyncAnthropic",
            return_value=MagicMock(),
        ),
        patch(
            "app.ai.runtime.generation.observability.token_counter.genai.Client",
            return_value=MagicMock(),
        ),
    ):
        return TokenCounter()


# ---------------------------------------------------------------------------
# Empty
# ---------------------------------------------------------------------------


async def test_empty() -> None:
    counter = _make_token_counter()

    assert await counter.count(GenerationProvider.OLLAMA, "llama3", "") == 1
    assert await counter.count(GenerationProvider.OLLAMA, "llama3", "   \n\t  ") == 1


# ---------------------------------------------------------------------------
# Large prompt
# ---------------------------------------------------------------------------


async def test_large_prompt() -> None:
    counter = _make_token_counter()
    text = " ".join(["word"] * 1000)

    estimated = await counter.count(GenerationProvider.OLLAMA, "llama3", text)

    assert estimated == int(1000 * 1.3)
    assert estimated > 1000


# ---------------------------------------------------------------------------
# Deterministic
# ---------------------------------------------------------------------------


async def test_estimation_consistency() -> None:
    counter = _make_token_counter()
    text = "The quick brown fox jumps over the lazy dog." * 50

    first = await counter.count(GenerationProvider.OLLAMA, "llama3", text)
    second = await counter.count(GenerationProvider.OLLAMA, "llama3", text)
    third = await counter.count(GenerationProvider.OLLAMA, "llama3", text)

    assert first == second == third
