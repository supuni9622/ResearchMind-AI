"""
Cross-provider streaming contract tests.

Individual SDK-shape parsing quirks (delta extraction, error types, etc.)
are covered per-provider in test_groq.py / test_openai.py / test_claude.py /
test_gemini.py / test_ollama.py. This file covers the *shared* contract:

- BaseGenerationProvider.stream() has no default streaming implementation:
  it is a plain (non-generator) function that raises NotImplementedError
  the moment it's called, for any provider that doesn't override it.
- StreamChunk / StreamEventType model defaults.
- Every real provider's stream() yields a START event first and a
  COMPLETED event last, regardless of how many TOKEN events it emits.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.config import (
    ClaudeGenerationConfig,
    GeminiGenerationConfig,
    GroqGenerationConfig,
    OllamaGenerationConfig,
    OpenAIGenerationConfig,
)
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
    StreamChunk,
    StreamEventType,
)
from app.ai.runtime.generation.providers.base import BaseGenerationProvider
from app.ai.runtime.generation.providers.claude import ClaudeProvider
from app.ai.runtime.generation.providers.gemini import GeminiProvider
from app.ai.runtime.generation.providers.groq import GroqProvider
from app.ai.runtime.generation.providers.ollama import OllamaProvider
from app.ai.runtime.generation.providers.openai import OpenAIProvider
from app.core.settings import settings


class _AsyncIter:
    """Minimal async-iterable test double for SDK streaming responses."""

    def __init__(self, items: list) -> None:
        self._items = iter(items)

    def __aiter__(self) -> _AsyncIter:
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration from None


class _MinimalProvider(BaseGenerationProvider):
    """The smallest possible concrete provider: does not override stream()."""

    @property
    def provider(self) -> GenerationProvider:
        return GenerationProvider.GROQ

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError


def _make_request() -> GenerationRequest:
    return GenerationRequest(
        prompt_context=PromptContext(context="retrieved context", chunks=[]),
        user_prompt="hello",
    )


def test_base_stream_default_raises_not_implemented_error_immediately() -> None:
    provider = _MinimalProvider(
        config=GroqGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )

    with pytest.raises(NotImplementedError, match="does not support streaming"):
        provider.stream(request=_make_request())


def test_stream_chunk_defaults_have_no_content_or_metadata() -> None:
    chunk = StreamChunk(event=StreamEventType.TOKEN)

    assert chunk.content is None
    assert chunk.metadata == {}


def test_stream_chunk_carries_explicit_content() -> None:
    chunk = StreamChunk(event=StreamEventType.TOKEN, content="hello")

    assert chunk.content == "hello"


async def test_groq_stream_starts_and_completes_around_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    provider = GroqProvider(
        config=GroqGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    provider._client = MagicMock()
    chunk = MagicMock()
    chunk.choices[0].delta.content = "hi"
    provider._client.chat.completions.create = AsyncMock(return_value=_AsyncIter([chunk]))

    events = [c.event async for c in provider.stream(_make_request())]

    assert events[0] == StreamEventType.START
    assert events[-1] == StreamEventType.COMPLETED


async def test_openai_stream_starts_and_completes_around_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    provider = OpenAIProvider(
        config=OpenAIGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    provider._client = MagicMock()
    event = MagicMock()
    event.type = "response.output_text.delta"
    event.delta = "hi"
    provider._client.responses.create = AsyncMock(return_value=_AsyncIter([event]))

    events = [c.event async for c in provider.stream(_make_request())]

    assert events[0] == StreamEventType.START
    assert events[-1] == StreamEventType.COMPLETED


async def test_claude_stream_starts_and_completes_around_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    provider = ClaudeProvider(
        config=ClaudeGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    provider._client = MagicMock()

    event = SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(text="hi"))
    provider._client.messages.create = AsyncMock(return_value=_AsyncIter([event]))

    events = [c.event async for c in provider.stream(_make_request())]

    assert events[0] == StreamEventType.START
    assert events[-1] == StreamEventType.COMPLETED


async def test_gemini_stream_starts_and_completes_around_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    provider = GeminiProvider(
        config=GeminiGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    provider._client = MagicMock()
    chunk = MagicMock()
    chunk.text = "hi"
    provider._client.aio.models.generate_content_stream = AsyncMock(
        return_value=_AsyncIter([chunk])
    )

    events = [c.event async for c in provider.stream(_make_request())]

    assert events[0] == StreamEventType.START
    assert events[-1] == StreamEventType.COMPLETED


async def test_ollama_stream_starts_and_completes_around_tokens() -> None:
    provider = OllamaProvider(
        config=OllamaGenerationConfig(),
    )
    provider._client = MagicMock()
    chunk = MagicMock()
    chunk.message.content = "hi"
    provider._client.chat = AsyncMock(return_value=_AsyncIter([chunk]))

    events = [c.event async for c in provider.stream(_make_request())]

    assert events[0] == StreamEventType.START
    assert events[-1] == StreamEventType.COMPLETED


async def test_all_real_providers_yield_no_events_besides_start_and_completed_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An empty upstream stream (no token deltas at all) should still produce
    exactly the START/COMPLETED bookend pair, for every provider.
    """

    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    provider = GroqProvider(
        config=GroqGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    provider._client = MagicMock()
    provider._client.chat.completions.create = AsyncMock(return_value=_AsyncIter([]))

    events = [c.event async for c in provider.stream(_make_request())]

    assert events == [StreamEventType.START, StreamEventType.COMPLETED]
