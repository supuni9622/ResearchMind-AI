"""
Unit tests locking in the current (unimplemented) contract of the
compression providers that are still placeholders for future work.

EmbeddingCompressionProvider has real coverage in test_embedding.py now
that it's implemented -- if one of the remaining two starts passing
unexpectedly, it means that provider has been implemented too, and
this test should be replaced with real behavior coverage the same way.
"""

from __future__ import annotations

import pytest
from app.ai.knowledge.context.compression.models import CompressionRequest
from app.ai.knowledge.context.compression.providers.langchain import (
    LangChainCompressionProvider,
)
from app.ai.knowledge.context.compression.providers.llm import LLMCompressionProvider


async def test_langchain_compression_provider_is_not_yet_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await LangChainCompressionProvider().compress(CompressionRequest(chunks=[]))


async def test_llm_compression_provider_is_not_yet_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await LLMCompressionProvider().compress(CompressionRequest(chunks=[]))
