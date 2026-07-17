"""
Unit tests for LangChainCompressionProvider.

The LLM is faked with `FakeListChatModel` (LangChain's own deterministic
test double -- its `abatch` is explicitly overridden to preserve input
order with no concurrency, so responses map 1:1 to input chunks in the
order given) and injected via the constructor, so these tests never make
a network call.

Covers:
- 0 chunks short-circuits before touching the LLM
- A missing/blank query raises CompressionProviderError (the retriever
  is query-aware)
- Chunks the LLM extracts nothing relevant from ("NO_OUTPUT") are dropped
- Chunks the LLM extracts something from are kept with the extracted text
- Every non-content field (chunk_id, document_id, score, citation_id,
  page_numbers, metadata) survives untouched on kept chunks
- Statistics report accurate before/after counts and token estimates
- A provider-level failure is wrapped in CompressionProviderError
- A timeout is wrapped in CompressionTimeoutError
- No injected LLM and no configured API key raises CompressionProviderError
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.ai.knowledge.context.compression.enums import CompressionStrategy
from app.ai.knowledge.context.compression.exceptions import (
    CompressionProviderError,
    CompressionTimeoutError,
)
from app.ai.knowledge.context.compression.models import CompressionRequest
from app.ai.knowledge.context.compression.providers.langchain import (
    LangChainCompressionProvider,
)
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from tests.unit.ai.knowledge.context.factories import make_context_chunk

_SETTINGS_TARGET = "app.ai.knowledge.context.compression.providers.langchain.settings"


def _make_provider(responses: list[str]) -> LangChainCompressionProvider:
    return LangChainCompressionProvider(llm=FakeListChatModel(responses=responses))


async def test_compress_with_no_chunks_never_builds_an_llm() -> None:
    provider = LangChainCompressionProvider(llm=None)

    result = await provider.compress(CompressionRequest(chunks=[], query="revenue?"))

    assert result.chunks == []
    assert result.strategy == CompressionStrategy.LANGCHAIN_CONTEXTUAL


async def test_compress_without_a_query_raises() -> None:
    chunk = make_context_chunk()
    provider = _make_provider(["irrelevant"])

    with pytest.raises(CompressionProviderError, match="query"):
        await provider.compress(CompressionRequest(chunks=[chunk], query=None))


async def test_compress_without_a_query_string_only_whitespace_raises() -> None:
    chunk = make_context_chunk()
    provider = _make_provider(["irrelevant"])

    with pytest.raises(CompressionProviderError, match="query"):
        await provider.compress(CompressionRequest(chunks=[chunk], query="   "))


async def test_compress_drops_chunks_with_nothing_relevant() -> None:
    relevant = make_context_chunk(content="OpenAI revenue grew 30% in 2025.")
    irrelevant = make_context_chunk(content="The weather in Paris was mild.")
    # Responses map to chunks in order: relevant kept, irrelevant dropped.
    provider = _make_provider(["OpenAI revenue grew 30% in 2025.", "NO_OUTPUT"])

    result = await provider.compress(
        CompressionRequest(chunks=[relevant, irrelevant], query="How did OpenAI's revenue change?")
    )

    assert [chunk.chunk_id for chunk in result.chunks] == [relevant.chunk_id]
    assert result.chunks[0].content == "OpenAI revenue grew 30% in 2025."


async def test_compress_preserves_every_field_except_content() -> None:
    chunk = make_context_chunk(
        content="OpenAI revenue grew 30% in 2025, driven by enterprise adoption.",
        score=0.87,
        citation_id="cite-1",
        page_numbers=[4, 5],
        metadata={"source_id": "doc-42", "document_type": "10-K"},
    )
    provider = _make_provider(["OpenAI revenue grew 30%."])

    result = await provider.compress(
        CompressionRequest(chunks=[chunk], query="revenue growth?"),
    )

    [restored] = result.chunks
    assert restored.content == "OpenAI revenue grew 30%."
    assert restored.chunk_id == chunk.chunk_id
    assert restored.document_id == chunk.document_id
    assert restored.score == chunk.score
    assert restored.citation_id == chunk.citation_id
    assert restored.page_numbers == chunk.page_numbers
    assert restored.metadata == chunk.metadata


async def test_compress_reports_accurate_statistics() -> None:
    kept = make_context_chunk(content="a" * 40)
    dropped = make_context_chunk(content="b" * 40)
    provider = _make_provider(["a" * 20, "NO_OUTPUT"])

    result = await provider.compress(
        CompressionRequest(chunks=[kept, dropped], query="q"),
    )

    assert result.statistics.original_chunks == 2
    assert result.statistics.compressed_chunks == 1
    assert result.statistics.removed_chunks == 1
    assert result.statistics.original_tokens == (40 // 4) * 2
    assert result.statistics.compressed_tokens == 20 // 4
    assert result.statistics.estimated_saved_tokens == result.statistics.original_tokens - (20 // 4)
    assert result.statistics.duration_ms >= 0


async def test_compress_wraps_a_provider_failure() -> None:
    chunk = make_context_chunk()
    provider = _make_provider(["whatever"])

    with (
        patch.object(provider, "_compress_documents", AsyncMock(side_effect=RuntimeError("boom"))),
        pytest.raises(CompressionProviderError, match="boom"),
    ):
        await provider.compress(CompressionRequest(chunks=[chunk], query="q"))


async def test_compress_wraps_a_timeout() -> None:
    chunk = make_context_chunk()
    provider = _make_provider(["whatever"])

    with (
        patch.object(provider, "_compress_documents", AsyncMock(side_effect=TimeoutError())),
        pytest.raises(CompressionTimeoutError),
    ):
        await provider.compress(CompressionRequest(chunks=[chunk], query="q"))


async def test_compress_without_an_llm_or_api_key_raises() -> None:
    chunk = make_context_chunk()
    provider = LangChainCompressionProvider(llm=None)

    with patch(_SETTINGS_TARGET) as mock_settings:
        mock_settings.openai_api_key = None

        with pytest.raises(CompressionProviderError, match="OPENAI_API_KEY"):
            await provider.compress(CompressionRequest(chunks=[chunk], query="q"))
