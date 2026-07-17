"""
Unit tests for LLMCompressionProvider.

`GenerationService.generate()` is faked with an `AsyncMock` injected via
the constructor, so these tests never make a network call or construct a
real provider registry.

Covers:
- 0 chunks short-circuits before calling the generation service
- A missing/blank query raises CompressionProviderError (the compression
  prompt is query-aware)
- A blank chunk is returned unchanged without calling the generation
  service
- A summarized chunk keeps every field except content
- An empty summary falls back to the original chunk's content
- A per-chunk generation failure falls back to that chunk's original
  content without failing the whole batch
- No chunk is ever dropped -- compressed_chunks always equals
  original_chunks and removed_chunks is always 0
- Statistics report accurate token estimates and duration
- generate() is called with the configured provider/temperature/max_tokens
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.context.compression.enums import CompressionStrategy
from app.ai.knowledge.context.compression.exceptions import CompressionProviderError
from app.ai.knowledge.context.compression.models import CompressionRequest, LLMCompressionConfig
from app.ai.knowledge.context.compression.providers.llm import LLMCompressionProvider
from app.ai.runtime.generation.enums import GenerationProvider

from tests.unit.ai.knowledge.context.factories import make_context_chunk


def _generation_result(content: str) -> SimpleNamespace:
    # The provider only reads `.content` off whatever generate() returns --
    # a real GenerationResult isn't needed (and building one requires
    # fields, like `request`, this provider never touches).
    return SimpleNamespace(content=content)


def _make_provider(
    *,
    side_effect=None,
    config: LLMCompressionConfig | None = None,
) -> tuple[LLMCompressionProvider, AsyncMock]:
    generation_service = AsyncMock()
    generation_service.generate = AsyncMock(side_effect=side_effect)
    provider = LLMCompressionProvider(generation_service=generation_service, config=config)
    return provider, generation_service


async def test_compress_with_no_chunks_never_calls_generation_service() -> None:
    provider, generation_service = _make_provider()

    result = await provider.compress(CompressionRequest(chunks=[], query="revenue?"))

    assert result.chunks == []
    assert result.strategy == CompressionStrategy.LLM
    generation_service.generate.assert_not_awaited()


async def test_compress_without_a_query_raises() -> None:
    chunk = make_context_chunk()
    provider, _ = _make_provider()

    with pytest.raises(CompressionProviderError, match="query"):
        await provider.compress(CompressionRequest(chunks=[chunk], query=None))


async def test_compress_without_a_query_string_only_whitespace_raises() -> None:
    chunk = make_context_chunk()
    provider, _ = _make_provider()

    with pytest.raises(CompressionProviderError, match="query"):
        await provider.compress(CompressionRequest(chunks=[chunk], query="   "))


async def test_compress_skips_blank_chunks_without_calling_generation_service() -> None:
    blank = make_context_chunk(content="   ")
    provider, generation_service = _make_provider()

    result = await provider.compress(CompressionRequest(chunks=[blank], query="q"))

    assert result.chunks[0].content == "   "
    generation_service.generate.assert_not_awaited()


async def test_compress_replaces_content_with_the_summary() -> None:
    chunk = make_context_chunk(content="OpenAI revenue grew 30% in 2025, driven by enterprise.")
    provider, _ = _make_provider(side_effect=[_generation_result("OpenAI revenue grew 30%.")])

    result = await provider.compress(
        CompressionRequest(chunks=[chunk], query="How did revenue change?")
    )

    assert result.chunks[0].content == "OpenAI revenue grew 30%."


async def test_compress_preserves_every_field_except_content() -> None:
    chunk = make_context_chunk(
        content="OpenAI revenue grew 30% in 2025.",
        score=0.87,
        citation_id="cite-1",
        page_numbers=[4, 5],
        metadata={"source_id": "doc-42", "document_type": "10-K"},
    )
    provider, _ = _make_provider(side_effect=[_generation_result("OpenAI revenue grew 30%.")])

    result = await provider.compress(CompressionRequest(chunks=[chunk], query="revenue growth?"))

    [restored] = result.chunks
    assert restored.content == "OpenAI revenue grew 30%."
    assert restored.chunk_id == chunk.chunk_id
    assert restored.document_id == chunk.document_id
    assert restored.score == chunk.score
    assert restored.citation_id == chunk.citation_id
    assert restored.page_numbers == chunk.page_numbers
    assert restored.metadata == chunk.metadata


async def test_compress_falls_back_to_original_content_when_summary_is_empty() -> None:
    chunk = make_context_chunk(content="original content")
    provider, _ = _make_provider(side_effect=[_generation_result("   ")])

    result = await provider.compress(CompressionRequest(chunks=[chunk], query="q"))

    assert result.chunks[0].content == "original content"


async def test_compress_falls_back_to_original_content_on_a_per_chunk_failure() -> None:
    ok = make_context_chunk(content="a" * 40)
    failing = make_context_chunk(content="b" * 40)

    def _side_effect(*, request, provider):
        if request.prompt_context.context == failing.content:
            raise RuntimeError("boom")
        return _generation_result("a" * 10)

    provider, _ = _make_provider(side_effect=_side_effect)

    result = await provider.compress(CompressionRequest(chunks=[ok, failing], query="q"))

    contents = {chunk.chunk_id: chunk.content for chunk in result.chunks}
    assert contents[ok.chunk_id] == "a" * 10
    assert contents[failing.chunk_id] == "b" * 40


async def test_compress_never_drops_a_chunk() -> None:
    kept = make_context_chunk(content="a" * 40)
    also_kept = make_context_chunk(content="b" * 40)
    provider, _ = _make_provider(side_effect=RuntimeError("boom"))

    result = await provider.compress(CompressionRequest(chunks=[kept, also_kept], query="q"))

    assert result.statistics.original_chunks == 2
    assert result.statistics.compressed_chunks == 2
    assert result.statistics.removed_chunks == 0
    assert len(result.chunks) == 2


async def test_compress_reports_accurate_statistics() -> None:
    chunk = make_context_chunk(content="a" * 40)
    provider, _ = _make_provider(side_effect=[_generation_result("a" * 20)])

    result = await provider.compress(CompressionRequest(chunks=[chunk], query="q"))

    assert result.statistics.original_tokens == 40 // 4
    assert result.statistics.compressed_tokens == 20 // 4
    assert result.statistics.estimated_saved_tokens == (40 // 4) - (20 // 4)
    assert result.statistics.duration_ms >= 0


async def test_compress_calls_generation_service_with_configured_settings() -> None:
    chunk = make_context_chunk(content="some content")
    config = LLMCompressionConfig(
        provider=GenerationProvider.OPENAI,
        max_tokens=123,
        temperature=0.5,
    )
    provider, generation_service = _make_provider(
        side_effect=[_generation_result("summary")],
        config=config,
    )

    await provider.compress(CompressionRequest(chunks=[chunk], query="q"))

    _, kwargs = generation_service.generate.call_args
    assert kwargs["provider"] == GenerationProvider.OPENAI
    assert kwargs["request"].max_tokens == 123
    assert kwargs["request"].temperature == 0.5
    assert kwargs["request"].prompt_context.context == "some content"
    assert "q" in kwargs["request"].user_prompt
