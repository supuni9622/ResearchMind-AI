"""
Unit tests for CompressionService.

Covers:
- compress resolves the requested strategy's provider and delegates
  the request to it, returning its result unchanged
- a not-found strategy propagates the registry's ValueError
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.context.compression.enums import CompressionStrategy
from app.ai.knowledge.context.compression.models import CompressionRequest
from app.ai.knowledge.context.compression.registry import CompressionRegistry
from app.ai.knowledge.context.compression.service import CompressionService


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
