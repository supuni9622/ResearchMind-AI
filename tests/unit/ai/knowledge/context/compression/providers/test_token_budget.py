"""
Unit tests for TokenBudgetCompressionProvider.

Covers:
- Chunks are considered highest-score first
- Chunks that fit within the token budget are all kept
- A chunk too large to fit is skipped, but the packing continues so a
  smaller, lower-scored chunk after it can still fill the remaining
  budget (this "continue" rather than "stop at first overflow" bin
  packing behavior is intentional -- pinned here so a future refactor
  doesn't silently change it)
- request.max_tokens overrides the provider's default budget
- Statistics report original/compressed/removed chunk counts correctly
- Empty input produces an empty result with zeroed statistics
"""

from __future__ import annotations

from app.ai.knowledge.context.compression.enums import CompressionStrategy
from app.ai.knowledge.context.compression.models import CompressionRequest
from app.ai.knowledge.context.compression.providers.token_budget import (
    TokenBudgetCompressionProvider,
)

from tests.unit.ai.knowledge.context.factories import make_context_chunk


async def test_compress_prefers_highest_score_first() -> None:
    low = make_context_chunk(content="a" * 40, score=0.1)
    high = make_context_chunk(content="b" * 40, score=0.9)
    provider = TokenBudgetCompressionProvider()

    # Budget only large enough for one chunk (~10 tokens at 4 chars/token).
    result = await provider.compress(
        CompressionRequest(chunks=[low, high], max_tokens=10),
    )

    assert result.chunks == [high]


async def test_compress_keeps_all_chunks_that_fit_the_budget() -> None:
    chunks = [make_context_chunk(content="x" * 40, score=score) for score in (0.9, 0.5, 0.1)]
    provider = TokenBudgetCompressionProvider()

    result = await provider.compress(
        CompressionRequest(chunks=chunks, max_tokens=1000),
    )

    assert len(result.chunks) == 3
    assert result.statistics.removed_chunks == 0


async def test_compress_skips_an_oversized_chunk_but_keeps_packing_smaller_ones() -> None:
    # ~25 tokens (100 chars // 4), won't fit after the small chunk below.
    oversized = make_context_chunk(content="x" * 100, score=0.9)
    # ~5 tokens, fits even though it's lower priority.
    small = make_context_chunk(content="y" * 20, score=0.1)
    provider = TokenBudgetCompressionProvider()

    result = await provider.compress(
        CompressionRequest(chunks=[oversized, small], max_tokens=10),
    )

    assert result.chunks == [small]
    assert result.statistics.removed_chunks == 1


async def test_compress_uses_default_budget_when_max_tokens_is_none() -> None:
    chunk = make_context_chunk(content="x" * 40)
    provider = TokenBudgetCompressionProvider()
    assert provider.DEFAULT_MAX_TOKENS > 0

    result = await provider.compress(
        CompressionRequest(chunks=[chunk], max_tokens=None),
    )

    assert result.chunks == [chunk]


async def test_compress_reports_accurate_statistics() -> None:
    kept = make_context_chunk(content="x" * 20, score=0.9)
    dropped = make_context_chunk(content="y" * 100, score=0.1)
    provider = TokenBudgetCompressionProvider()

    result = await provider.compress(
        CompressionRequest(chunks=[kept, dropped], max_tokens=10),
    )

    assert result.strategy == CompressionStrategy.TOKEN_BUDGET
    assert result.statistics.original_chunks == 2
    assert result.statistics.compressed_chunks == 1
    assert result.statistics.removed_chunks == 1


async def test_compress_empty_input_returns_empty_result() -> None:
    provider = TokenBudgetCompressionProvider()

    result = await provider.compress(CompressionRequest(chunks=[], max_tokens=100))

    assert result.chunks == []
    assert result.statistics.original_chunks == 0
    assert result.statistics.compressed_chunks == 0
    assert result.statistics.removed_chunks == 0
