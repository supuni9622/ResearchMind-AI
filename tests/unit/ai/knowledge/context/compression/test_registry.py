"""
Unit tests for CompressionRegistry.

Covers:
- get resolves a registered provider for its strategy
- get raises ValueError for an unregistered strategy
- register overwrites any provider previously registered under the
  same strategy
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.ai.knowledge.context.compression.enums import CompressionStrategy
from app.ai.knowledge.context.compression.registry import CompressionRegistry


def test_get_resolves_a_registered_provider() -> None:
    provider = MagicMock()
    registry = CompressionRegistry()
    registry.register(CompressionStrategy.TOKEN_BUDGET, provider)

    assert registry.get(CompressionStrategy.TOKEN_BUDGET) is provider


def test_get_raises_for_an_unregistered_strategy() -> None:
    registry = CompressionRegistry()

    with pytest.raises(ValueError, match="token_budget"):
        registry.get(CompressionStrategy.TOKEN_BUDGET)


def test_register_overwrites_the_previous_provider_for_a_strategy() -> None:
    first = MagicMock()
    second = MagicMock()
    registry = CompressionRegistry()

    registry.register(CompressionStrategy.LLM, first)
    registry.register(CompressionStrategy.LLM, second)

    assert registry.get(CompressionStrategy.LLM) is second
