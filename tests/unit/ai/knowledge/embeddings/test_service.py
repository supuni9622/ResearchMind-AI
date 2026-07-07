"""
Unit tests for EmbeddingService.

Covers:
- Successful delegation to the resolved provider
- Provider resolution failure propagates from the registry
- Validation failure for chunk artifacts with no chunks
- Validation failure for chunks containing no text
- Embedding cache: full hit, full miss, partial hit/miss, and cache
  population after generating new embeddings
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.cache.embeddings.interfaces import EmbeddingCache
from app.ai.knowledge.cache.embeddings.key import build_embedding_cache_key
from app.ai.knowledge.chunking.artifacts.models import (
    ChunkArtifact,
    ChunkArtifactDocument,
    ChunkArtifactStatistics,
    ChunkArtifactStrategy,
)
from app.ai.knowledge.chunking.enums import ChunkContentType, ChunkingStrategy
from app.ai.knowledge.chunking.models import (
    Chunk,
    ChunkContent,
    ChunkExperiment,
    ChunkProvenance,
    ChunkStatistics,
    ChunkStructure,
)
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.exceptions import (
    EmbeddingProviderNotFoundError,
    EmbeddingValidationError,
)
from app.ai.knowledge.embeddings.factory import EmbeddingFactory
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry
from app.ai.knowledge.embeddings.service import EmbeddingService

_DOCUMENT_ID = uuid.uuid4()
_MODEL = "test-model"
_FINGERPRINT = "fingerprint"


class _FakeCache(EmbeddingCache):
    """
    In-memory EmbeddingCache double for exercising hit/miss behavior.
    """

    def __init__(self, initial: dict[str, list[float]] | None = None) -> None:
        self.store: dict[str, list[float]] = dict(initial or {})
        self.set_many_calls: list[dict[str, list[float]]] = []

    async def get_many(self, keys: list[str]) -> dict[str, list[float]]:
        return {key: self.store[key] for key in keys if key in self.store}

    async def set_many(self, entries: dict[str, list[float]]) -> None:
        self.set_many_calls.append(entries)
        self.store.update(entries)


def _key_for(chunk: Chunk) -> str:
    return build_embedding_cache_key(
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        model=_MODEL,
        configuration_fingerprint=_FINGERPRINT,
        text=chunk.content.text,
    )


def _make_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.provider = EmbeddingProvider.SENTENCE_TRANSFORMERS
    provider.model = _MODEL
    provider.version = "1.0"
    provider.configuration_fingerprint = _FINGERPRINT

    def _embed(artifact: ChunkArtifact) -> list:
        return [
            EmbeddingFactory.from_vector(
                chunk=chunk,
                vector=[0.9],
                provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
                model=_MODEL,
                provider_version="1.0",
                configuration_fingerprint=_FINGERPRINT,
            )
            for chunk in artifact.chunks
        ]

    provider.embed = AsyncMock(side_effect=_embed)
    return provider


def _make_chunk(text: str) -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        index=0,
        total_chunks=1,
        content=ChunkContent(text=text, content_type=ChunkContentType.TEXT),
        structure=ChunkStructure(),
        statistics=ChunkStatistics(character_count=len(text)),
        provenance=ChunkProvenance(
            document_id=_DOCUMENT_ID,
            filename="test.pdf",
            parser="docling",
        ),
        experiment=ChunkExperiment(
            strategy=ChunkingStrategy.FIXED,
            configuration_fingerprint="fingerprint",
        ),
    )


def _make_chunk_artifact(chunks: list[Chunk]) -> ChunkArtifact:
    return ChunkArtifact(
        document=ChunkArtifactDocument(
            document_id=_DOCUMENT_ID,
            filename="test.pdf",
            parser="docling",
        ),
        strategy=ChunkArtifactStrategy(
            strategy=ChunkingStrategy.FIXED,
            strategy_version="1.0",
            configuration_fingerprint="fingerprint",
        ),
        statistics=ChunkArtifactStatistics(),
        chunks=chunks,
    )


async def test_embed_delegates_to_resolved_provider() -> None:
    chunk = _make_chunk("hello world")
    artifact = _make_chunk_artifact([chunk])

    embedding = EmbeddingFactory.from_vector(
        chunk=chunk,
        vector=[0.1, 0.2],
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        model="test-model",
        provider_version="1.0",
        configuration_fingerprint="fingerprint",
    )

    provider = AsyncMock()
    provider.provider = EmbeddingProvider.SENTENCE_TRANSFORMERS
    provider.model = "test-model"
    provider.version = "1.0"
    provider.configuration_fingerprint = "fingerprint"
    provider.embed = AsyncMock(return_value=[embedding])

    registry = EmbeddingRegistry()
    registry.register(provider)

    service = EmbeddingService(registry=registry)

    result = await service.embed(
        artifact=artifact,
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
    )

    assert result == [embedding]
    provider.embed.assert_awaited_once_with(artifact)


async def test_embed_raises_when_provider_not_registered() -> None:
    service = EmbeddingService(registry=EmbeddingRegistry())
    artifact = _make_chunk_artifact([_make_chunk("hello world")])

    with pytest.raises(EmbeddingProviderNotFoundError):
        await service.embed(
            artifact=artifact,
            provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        )


async def test_embed_raises_when_chunk_artifact_has_no_chunks() -> None:
    provider = AsyncMock()
    provider.provider = EmbeddingProvider.SENTENCE_TRANSFORMERS

    registry = EmbeddingRegistry()
    registry.register(provider)

    service = EmbeddingService(registry=registry)
    artifact = _make_chunk_artifact([])

    with pytest.raises(EmbeddingValidationError, match="no chunks"):
        await service.embed(
            artifact=artifact,
            provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        )


async def test_embed_raises_when_a_chunk_has_no_text() -> None:
    provider = AsyncMock()
    provider.provider = EmbeddingProvider.SENTENCE_TRANSFORMERS

    registry = EmbeddingRegistry()
    registry.register(provider)

    service = EmbeddingService(registry=registry)
    artifact = _make_chunk_artifact([_make_chunk("   ")])

    with pytest.raises(EmbeddingValidationError, match="no text"):
        await service.embed(
            artifact=artifact,
            provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        )


async def test_embed_skips_provider_entirely_on_full_cache_hit() -> None:
    chunk = _make_chunk("hello world")
    artifact = _make_chunk_artifact([chunk])

    cache = _FakeCache({_key_for(chunk): [0.1, 0.2, 0.3]})
    provider = _make_provider()

    registry = EmbeddingRegistry()
    registry.register(provider)

    service = EmbeddingService(registry=registry, cache=cache)

    result = await service.embed(
        artifact=artifact,
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
    )

    provider.embed.assert_not_awaited()
    assert len(result) == 1
    assert result[0].vector.values == [0.1, 0.2, 0.3]
    assert result[0].provenance.chunk_id == chunk.id


async def test_embed_calls_provider_for_full_cache_miss_and_populates_cache() -> None:
    chunk = _make_chunk("hello world")
    artifact = _make_chunk_artifact([chunk])

    cache = _FakeCache()
    provider = _make_provider()

    registry = EmbeddingRegistry()
    registry.register(provider)

    service = EmbeddingService(registry=registry, cache=cache)

    result = await service.embed(
        artifact=artifact,
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
    )

    provider.embed.assert_awaited_once()
    assert len(result) == 1
    assert result[0].vector.values == [0.9]

    key = _key_for(chunk)
    assert cache.store[key] == [0.9]


async def test_embed_only_sends_cache_misses_to_the_provider_and_preserves_order() -> None:
    cached_chunk = _make_chunk("cached text")
    missing_chunk = _make_chunk("missing text")
    artifact = _make_chunk_artifact([cached_chunk, missing_chunk])

    cache = _FakeCache({_key_for(cached_chunk): [0.5, 0.5]})
    provider = _make_provider()

    registry = EmbeddingRegistry()
    registry.register(provider)

    service = EmbeddingService(registry=registry, cache=cache)

    result = await service.embed(
        artifact=artifact,
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
    )

    provider.embed.assert_awaited_once()
    sent_artifact = provider.embed.await_args.args[0]
    assert [chunk.id for chunk in sent_artifact.chunks] == [missing_chunk.id]

    # Result order matches the original chunk order, not hit/miss order.
    assert [embedding.provenance.chunk_id for embedding in result] == [
        cached_chunk.id,
        missing_chunk.id,
    ]
    assert result[0].vector.values == [0.5, 0.5]
    assert result[1].vector.values == [0.9]

    assert cache.store[_key_for(missing_chunk)] == [0.9]
    assert _key_for(cached_chunk) not in cache.set_many_calls[0]
