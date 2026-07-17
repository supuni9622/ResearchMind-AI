"""
Unit tests locking in the current (unimplemented) contract of the
compression providers that are still placeholders for future work.

EmbeddingCompressionProvider and LangChainCompressionProvider have real
coverage now that they're implemented (see test_embedding.py and
test_langchain.py) -- if LLMCompressionProvider starts passing
unexpectedly, it means it's been implemented too, and this test should
be replaced with real behavior coverage the same way.
"""

from __future__ import annotations

import pytest
from app.ai.knowledge.context.compression.models import CompressionRequest
from app.ai.knowledge.context.compression.providers.llm import LLMCompressionProvider


async def test_llm_compression_provider_is_not_yet_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await LLMCompressionProvider().compress(CompressionRequest(chunks=[]))
