"""
Unit tests for CompressionService.

Covers:
- compress resolves the requested strategy's provider and delegates
  the request to it, returning its result unchanged
- a not-found strategy propagates the registry's ValueError (a
  caller/wiring bug, not a runtime compression failure)
- a provider raising CompressionError falls back to returning the
  original, uncompressed chunks instead of raising -- compression must
  never break generation
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.context.compression.enums import CompressionStrategy
from app.ai.knowledge.context.compression.exceptions import CompressionProviderError
from app.ai.knowledge.context.compression.models import CompressionRequest
from app.ai.knowledge.context.compression.registry import CompressionRegistry
from app.ai.knowledge.context.compression.service import CompressionService

from tests.unit.ai.knowledge.context.factories import make_context_chunk


async def test_compress_delegates_to_the_resolved_provider() -> None:
    provider = AsyncMock()
    expected_result = object()
    provider.compress = AsyncMock(return_value=expected_result)
    registry = CompressionRegistry()
    registry.register(CompressionStrategy.TOKEN_BUDGET, provider)
    service = CompressionService(registry=registry)
    request = CompressionRequest(chunks=[])

    result = await service.compress(strategy=CompressionStrategy.TOKEN_BUDGET, request=request)

    assert result is expected_result
    provider.compress.assert_awaited_once_with(request)


async def test_compress_raises_when_strategy_is_not_registered() -> None:
    service = CompressionService(registry=CompressionRegistry())
    request = CompressionRequest(chunks=[])

    with pytest.raises(ValueError, match="llm"):
        await service.compress(strategy=CompressionStrategy.LLM, request=request)


async def test_compress_falls_back_to_original_chunks_when_the_provider_fails() -> None:
    chunks = [make_context_chunk(), make_context_chunk()]
    provider = AsyncMock()
    provider.compress = AsyncMock(side_effect=CompressionProviderError("boom"))
    registry = CompressionRegistry()
    registry.register(CompressionStrategy.LANGCHAIN_CONTEXTUAL, provider)
    service = CompressionService(registry=registry)
    request = CompressionRequest(chunks=chunks, query="q")

    result = await service.compress(
        strategy=CompressionStrategy.LANGCHAIN_CONTEXTUAL, request=request
    )

    assert result.chunks == chunks
    assert result.strategy == CompressionStrategy.LANGCHAIN_CONTEXTUAL
    assert result.statistics.original_chunks == 2
    assert result.statistics.compressed_chunks == 2
    assert result.statistics.removed_chunks == 0
