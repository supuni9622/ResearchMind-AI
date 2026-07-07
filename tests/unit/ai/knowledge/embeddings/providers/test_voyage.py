"""
Unit tests for VoyageAIEmbeddingProvider.

Covers:
- Provider and model identifiers
- The Voyage AI client is invoked with the configured model and input type
- Conversion of the SDK response into canonical Embedding models
- Integer vector values returned by the SDK are coerced to floats
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

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
from app.ai.knowledge.embeddings.config import VoyageAIEmbeddingConfig
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.providers.voyage import VoyageAIEmbeddingProvider

_DOCUMENT_ID = uuid.uuid4()


def _make_chunk(text: str, index: int = 0) -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        index=index,
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


def _make_client(embeddings: list[list[float]]) -> MagicMock:
    client = MagicMock()
    client.embed.return_value = SimpleNamespace(embeddings=embeddings)
    return client


def test_provider_identifiers_reflect_configuration() -> None:
    client = _make_client(embeddings=[])
    config = VoyageAIEmbeddingConfig(model_name="voyage-3-large")
    provider = VoyageAIEmbeddingProvider(config=config, client=client)

    assert provider.provider == EmbeddingProvider.VOYAGE_AI
    assert provider.model == "voyage-3-large"


async def test_embed_calls_client_with_configured_model_and_input_type() -> None:
    chunks = [_make_chunk("hello"), _make_chunk("world", index=1)]
    client = _make_client(embeddings=[[0.1, 0.2], [0.3, 0.4]])
    config = VoyageAIEmbeddingConfig(model_name="voyage-3-large", input_type="query")
    provider = VoyageAIEmbeddingProvider(config=config, client=client)

    await provider.embed(_make_chunk_artifact(chunks))

    client.embed.assert_called_once_with(
        texts=["hello", "world"],
        model="voyage-3-large",
        input_type="query",
    )


async def test_embed_converts_response_into_canonical_embeddings() -> None:
    chunk = _make_chunk("hello world")
    client = _make_client(embeddings=[[0.1, 0.2, 0.3]])
    provider = VoyageAIEmbeddingProvider(
        config=VoyageAIEmbeddingConfig(),
        client=client,
    )

    embeddings = await provider.embed(_make_chunk_artifact([chunk]))

    assert len(embeddings) == 1
    embedding = embeddings[0]

    assert embedding.provenance.document_id == chunk.provenance.document_id
    assert embedding.provenance.chunk_id == chunk.id
    assert embedding.provider.provider == EmbeddingProvider.VOYAGE_AI
    assert embedding.provider.model == provider.model
    assert embedding.vector.values == [0.1, 0.2, 0.3]
    assert embedding.vector.dimensions == 3
    assert embedding.experiment.configuration_fingerprint == provider.configuration_fingerprint


async def test_embed_coerces_quantized_integer_vectors_to_floats() -> None:
    chunk = _make_chunk("hello world")
    client = _make_client(embeddings=[[1, 0, -1]])
    provider = VoyageAIEmbeddingProvider(
        config=VoyageAIEmbeddingConfig(),
        client=client,
    )

    embeddings = await provider.embed(_make_chunk_artifact([chunk]))

    values = embeddings[0].vector.values
    assert values == [1.0, 0.0, -1.0]
    assert all(isinstance(value, float) for value in values)
