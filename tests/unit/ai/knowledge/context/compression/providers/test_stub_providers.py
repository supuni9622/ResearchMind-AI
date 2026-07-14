"""
Unit tests locking in the current (unimplemented) contract of the
compression providers that are placeholders for future work.

If one of these starts passing unexpectedly, it means the provider has
been implemented and this test should be replaced with real coverage
of its behavior instead of an expected-failure check.
"""

from __future__ import annotations

import pytest
from app.ai.knowledge.context.compression.models import CompressionRequest
from app.ai.knowledge.context.compression.providers.embedding import (
    EmbeddingCompressionProvider,
)
from app.ai.knowledge.context.compression.providers.langchain import (
    LangChainCompressionProvider,
)
from app.ai.knowledge.context.compression.providers.llm import LLMCompressionProvider


async def test_embedding_compression_provider_is_not_yet_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await EmbeddingCompressionProvider().compress(CompressionRequest(chunks=[]))


async def test_langchain_compression_provider_is_not_yet_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await LangChainCompressionProvider().compress(CompressionRequest(chunks=[]))


async def test_llm_compression_provider_is_not_yet_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await LLMCompressionProvider().compress(CompressionRequest(chunks=[]))
