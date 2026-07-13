"""
Unit tests for QueryEmbeddingService.

Covers:
- Cache hit returns the cached vector without calling any provider SDK
- Cache miss calls the Voyage AI client (default provider) and populates
  the cache with the result, coercing SDK values to float
- Cache miss calls the OpenAI client for the OpenAI provider
- An unsupported provider raises NotImplementedError instead of silently
  falling through
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.ai.knowledge.cache.query_embeddings.interfaces import QueryEmbeddingCache
from app.ai.knowledge.cache.query_embeddings.key import build_query_embedding_cache_key
from app.ai.knowledge.embeddings.config import (
    OpenAIEmbeddingConfig,
    VoyageAIEmbeddingConfig,
)
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.providers.openai import OpenAIEmbeddingProvider
from app.ai.knowledge.embeddings.providers.voyage import VoyageAIEmbeddingProvider
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry
from app.ai.knowledge.retrieval.query.dense_service import QueryEmbeddingService


class _FakeCache(QueryEmbeddingCache):
    """
    In-memory QueryEmbeddingCache double for exercising hit/miss behavior.
    """

    def __init__(self, initial: dict[str, list[float]] | None = None) -> None:
        self.store: dict[str, list[float]] = dict(initial or {})

    async def get(self, key: str) -> list[float] | None:
        return self.store.get(key)

    async def set(self, key: str, vector: list[float]) -> None:
        self.store[key] = vector


def _make_voyage_provider(
    *, embeddings: list[list[float]] | None = None
) -> tuple[VoyageAIEmbeddingProvider, MagicMock]:
    client = MagicMock()
    client.embed = MagicMock(
        return_value=SimpleNamespace(embeddings=embeddings or [[0.1, 0.2]]),
    )
    provider = VoyageAIEmbeddingProvider(config=VoyageAIEmbeddingConfig(), client=client)
    return provider, client


def _make_openai_provider(
    *, embedding: list[float] | None = None
) -> tuple[OpenAIEmbeddingProvider, MagicMock]:
    client = MagicMock()
    client.embeddings.create = MagicMock(
        return_value=SimpleNamespace(
            data=[SimpleNamespace(embedding=embedding or [0.3, 0.4])],
        ),
    )
    provider = OpenAIEmbeddingProvider(config=OpenAIEmbeddingConfig(), client=client)
    return provider, client


def _key_for(provider: VoyageAIEmbeddingProvider | OpenAIEmbeddingProvider, query: str) -> str:
    return build_query_embedding_cache_key(
        provider=provider.provider,
        model=provider.model,
        configuration_fingerprint=provider.configuration_fingerprint,
        query=query,
    )


async def test_embed_returns_cached_vector_without_calling_any_provider() -> None:
    voyage_provider, client = _make_voyage_provider()
    registry = EmbeddingRegistry()
    registry.register(voyage_provider)

    cache = _FakeCache({_key_for(voyage_provider, "what is rag?"): [0.9, 0.9]})
    service = QueryEmbeddingService(registry=registry, cache=cache)

    result = await service.embed("what is rag?", provider=EmbeddingProvider.VOYAGE_AI)

    assert result == [0.9, 0.9]
    client.embed.assert_not_called()


async def test_embed_calls_voyage_client_on_cache_miss_and_populates_cache() -> None:
    voyage_provider, client = _make_voyage_provider(embeddings=[[1, 2, 3]])
    registry = EmbeddingRegistry()
    registry.register(voyage_provider)

    cache = _FakeCache()
    service = QueryEmbeddingService(registry=registry, cache=cache)

    result = await service.embed("what is rag?", provider=EmbeddingProvider.VOYAGE_AI)

    client.embed.assert_called_once_with(
        texts=["what is rag?"],
        model=voyage_provider.model,
        input_type="query",
    )
    # SDK may return ints; the service must coerce every value to float.
    assert result == [1.0, 2.0, 3.0]
    assert all(isinstance(value, float) for value in result)
    assert cache.store[_key_for(voyage_provider, "what is rag?")] == [1.0, 2.0, 3.0]


async def test_embed_calls_openai_client_for_openai_provider() -> None:
    openai_provider, client = _make_openai_provider(embedding=[0.5, 0.6])
    registry = EmbeddingRegistry()
    registry.register(openai_provider)

    cache = _FakeCache()
    service = QueryEmbeddingService(registry=registry, cache=cache)

    result = await service.embed("what is rag?", provider=EmbeddingProvider.OPENAI)

    client.embeddings.create.assert_called_once_with(
        model=openai_provider.model,
        input=["what is rag?"],
    )
    assert result == [0.5, 0.6]
    assert cache.store[_key_for(openai_provider, "what is rag?")] == [0.5, 0.6]


async def test_embed_raises_not_implemented_for_an_unsupported_provider() -> None:
    unsupported_provider = MagicMock()
    unsupported_provider.provider = EmbeddingProvider.SENTENCE_TRANSFORMERS
    unsupported_provider.model = "some-model"
    unsupported_provider.configuration_fingerprint = "fingerprint"

    registry = EmbeddingRegistry()
    registry.register(unsupported_provider)

    service = QueryEmbeddingService(registry=registry, cache=_FakeCache())

    with pytest.raises(NotImplementedError, match="does not yet support"):
        await service.embed(
            "what is rag?",
            provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        )
