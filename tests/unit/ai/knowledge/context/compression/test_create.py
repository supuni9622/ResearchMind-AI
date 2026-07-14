"""
Unit test for the compression composition root.

Covers:
- create_compression_service() registers all four compression
  strategies, each resolving to the expected provider type
"""

from __future__ import annotations

from app.ai.knowledge.context.compression.create import create_compression_service
from app.ai.knowledge.context.compression.enums import CompressionStrategy
from app.ai.knowledge.context.compression.providers.embedding import (
    EmbeddingCompressionProvider,
)
from app.ai.knowledge.context.compression.providers.langchain import (
    LangChainCompressionProvider,
)
from app.ai.knowledge.context.compression.providers.llm import LLMCompressionProvider
from app.ai.knowledge.context.compression.providers.token_budget import (
    TokenBudgetCompressionProvider,
)


def test_create_compression_service_registers_every_strategy() -> None:
    service = create_compression_service()
    registry = service._registry  # noqa: SLF001

    assert isinstance(
        registry.get(CompressionStrategy.TOKEN_BUDGET), TokenBudgetCompressionProvider
    )
    assert isinstance(
        registry.get(CompressionStrategy.EMBEDDING_REDUNDANCY), EmbeddingCompressionProvider
    )
    assert isinstance(
        registry.get(CompressionStrategy.LANGCHAIN_CONTEXTUAL), LangChainCompressionProvider
    )
    assert isinstance(registry.get(CompressionStrategy.LLM), LLMCompressionProvider)
