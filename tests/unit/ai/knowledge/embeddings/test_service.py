"""
Unit tests for EmbeddingService.

Covers:
- Successful delegation to the resolved provider
- Provider resolution failure propagates from the registry
- Validation failure for chunk artifacts with no chunks
- Validation failure for chunks containing no text
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
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
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry
from app.ai.knowledge.embeddings.service import EmbeddingService

_DOCUMENT_ID = uuid.uuid4()


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
    provider = AsyncMock()
    provider.provider = EmbeddingProvider.SENTENCE_TRANSFORMERS
    provider.embed = AsyncMock(return_value=["embedding"])

    registry = EmbeddingRegistry()
    registry.register(provider)

    service = EmbeddingService(registry=registry)
    artifact = _make_chunk_artifact([_make_chunk("hello world")])

    result = await service.embed(
        artifact=artifact,
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
    )

    assert result == ["embedding"]
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
