"""
Unit tests for embedding batching behavior.

Covers:
- EmbeddingBatcher splits, remainder handling, and edge cases in isolation
- SentenceTransformerEmbeddingProvider batches chunks according to the
  configured batch size and preserves chunk order across batches
- VoyageAIEmbeddingProvider batches chunks into separate client.embed()
  calls according to the configured batch size
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
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
from app.ai.knowledge.embeddings.batching import EmbeddingBatcher
from app.ai.knowledge.embeddings.config import (
    SentenceTransformerEmbeddingConfig,
    VoyageAIEmbeddingConfig,
)
from app.ai.knowledge.embeddings.providers.sentence_transformers import (
    SentenceTransformerEmbeddingProvider,
)
from app.ai.knowledge.embeddings.providers.voyage import VoyageAIEmbeddingProvider

_DOCUMENT_ID = uuid.uuid4()

# ============================================================================
# EmbeddingBatcher
# ============================================================================


def test_batch_splits_items_into_equal_size_batches() -> None:
    batcher = EmbeddingBatcher(batch_size=2)

    batches = list(batcher.batch([1, 2, 3, 4, 5, 6]))

    assert batches == [[1, 2], [3, 4], [5, 6]]


def test_batch_yields_remainder_as_final_batch() -> None:
    batcher = EmbeddingBatcher(batch_size=3)

    batches = list(batcher.batch([1, 2, 3, 4, 5, 6, 7]))

    assert batches == [[1, 2, 3], [4, 5, 6], [7]]


def test_batch_size_larger_than_items_returns_single_batch() -> None:
    batcher = EmbeddingBatcher(batch_size=10)

    batches = list(batcher.batch([1, 2, 3]))

    assert batches == [[1, 2, 3]]


def test_batch_empty_iterable_yields_no_batches() -> None:
    batcher = EmbeddingBatcher(batch_size=2)

    assert list(batcher.batch([])) == []


def test_batch_size_property_returns_configured_value() -> None:
    batcher = EmbeddingBatcher(batch_size=5)

    assert batcher.batch_size == 5


@pytest.mark.parametrize("batch_size", [0, -1])
def test_constructor_raises_for_non_positive_batch_size(batch_size: int) -> None:
    with pytest.raises(ValueError, match="batch_size must be greater than zero"):
        EmbeddingBatcher(batch_size=batch_size)


# ============================================================================
# Provider batching integration
# ============================================================================


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


def _make_model() -> MagicMock:
    model = MagicMock()
    model.encode.side_effect = lambda texts, **_: np.array([[float(i)] for i in range(len(texts))])
    return model


async def test_embed_batches_chunks_according_to_configured_batch_size() -> None:
    model = _make_model()

    with patch(
        "app.ai.knowledge.embeddings.providers.sentence_transformers.SentenceTransformer",
        return_value=model,
    ):
        provider = SentenceTransformerEmbeddingProvider(
            SentenceTransformerEmbeddingConfig(batch_size=2),
        )

        chunks = [_make_chunk(f"chunk {i}", index=i) for i in range(5)]
        artifact = _make_chunk_artifact(chunks)

        embeddings = await provider.embed(artifact)

    assert model.encode.call_count == 3

    batch_texts = [call.args[0] for call in model.encode.call_args_list]
    assert batch_texts == [
        ["chunk 0", "chunk 1"],
        ["chunk 2", "chunk 3"],
        ["chunk 4"],
    ]

    assert [embedding.provenance.chunk_id for embedding in embeddings] == [
        chunk.id for chunk in chunks
    ]


async def test_embed_issues_single_batch_when_chunk_count_is_within_batch_size() -> None:
    model = _make_model()

    with patch(
        "app.ai.knowledge.embeddings.providers.sentence_transformers.SentenceTransformer",
        return_value=model,
    ):
        provider = SentenceTransformerEmbeddingProvider(
            SentenceTransformerEmbeddingConfig(batch_size=10),
        )

        chunks = [_make_chunk(f"chunk {i}", index=i) for i in range(3)]

        await provider.embed(_make_chunk_artifact(chunks))

    assert model.encode.call_count == 1


# ============================================================================
# Voyage AI batching integration
# ============================================================================


def _make_voyage_client() -> MagicMock:
    client = MagicMock()
    client.embed.side_effect = lambda texts, **_: SimpleNamespace(
        embeddings=[[float(i)] for i in range(len(texts))]
    )
    return client


async def test_voyage_embed_batches_chunks_according_to_configured_batch_size() -> None:
    client = _make_voyage_client()
    provider = VoyageAIEmbeddingProvider(
        config=VoyageAIEmbeddingConfig(batch_size=2),
        client=client,
    )

    chunks = [_make_chunk(f"chunk {i}", index=i) for i in range(5)]
    embeddings = await provider.embed(_make_chunk_artifact(chunks))

    assert client.embed.call_count == 3

    batch_texts = [call.kwargs["texts"] for call in client.embed.call_args_list]
    assert batch_texts == [
        ["chunk 0", "chunk 1"],
        ["chunk 2", "chunk 3"],
        ["chunk 4"],
    ]

    assert [embedding.provenance.chunk_id for embedding in embeddings] == [
        chunk.id for chunk in chunks
    ]


async def test_voyage_embed_issues_single_batch_when_chunk_count_is_within_batch_size() -> None:
    client = _make_voyage_client()
    provider = VoyageAIEmbeddingProvider(
        config=VoyageAIEmbeddingConfig(batch_size=10),
        client=client,
    )

    chunks = [_make_chunk(f"chunk {i}", index=i) for i in range(3)]

    await provider.embed(_make_chunk_artifact(chunks))

    assert client.embed.call_count == 1
