"""
Unit tests for EmbeddingCompressionProvider.

The local SentenceTransformer model is mocked (consistent with
tests/unit/ai/knowledge/embeddings/providers/test_sentence_transformers.py)
so these tests stay fast, deterministic, and independent of any model
download -- the encoded vectors are chosen directly to produce known
cosine similarities.

Covers:
- 0 or 1 chunks short-circuits before ever calling the model
- Near-duplicate chunks (similarity >= threshold) are collapsed,
  keeping the earlier chunk and dropping the later one
- Dissimilar chunks (similarity below threshold) are all kept
- A custom similarity_threshold is honored
- Statistics report accurate original/compressed/removed counts
- The model is called once with every chunk's content text
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
from app.ai.knowledge.context.compression.enums import CompressionStrategy
from app.ai.knowledge.context.compression.models import CompressionRequest
from app.ai.knowledge.context.compression.providers.embedding import (
    EmbeddingCompressionProvider,
)

from tests.unit.ai.knowledge.context.factories import make_context_chunk

_PATCH_TARGET = "app.ai.knowledge.context.compression.providers.embedding.get_local_embedding_model"


def _make_provider(
    vectors: list[list[float]],
    *,
    similarity_threshold: float | None = None,
) -> tuple[EmbeddingCompressionProvider, MagicMock]:
    model = MagicMock()
    model.encode = MagicMock(return_value=np.array(vectors))

    with patch(_PATCH_TARGET, return_value=model):
        provider = (
            EmbeddingCompressionProvider(similarity_threshold=similarity_threshold)
            if similarity_threshold is not None
            else EmbeddingCompressionProvider()
        )

    return provider, model


async def test_compress_with_no_chunks_never_calls_the_model() -> None:
    provider, model = _make_provider([])

    result = await provider.compress(CompressionRequest(chunks=[]))

    assert result.chunks == []
    model.encode.assert_not_called()


async def test_compress_with_one_chunk_never_calls_the_model() -> None:
    chunk = make_context_chunk()
    provider, model = _make_provider([])

    result = await provider.compress(CompressionRequest(chunks=[chunk]))

    assert result.chunks == [chunk]
    model.encode.assert_not_called()


async def test_compress_drops_the_later_near_duplicate_chunk() -> None:
    first = make_context_chunk(content="alpha")
    duplicate = make_context_chunk(content="alpha again")
    # Identical vectors -> cosine similarity 1.0, above the default 0.95.
    provider, _ = _make_provider([[1.0, 0.0], [1.0, 0.0]])

    result = await provider.compress(CompressionRequest(chunks=[first, duplicate]))

    assert result.chunks == [first]
    assert result.strategy == CompressionStrategy.EMBEDDING_REDUNDANCY
    assert result.statistics.removed_chunks == 1


async def test_compress_keeps_dissimilar_chunks() -> None:
    first = make_context_chunk(content="alpha")
    second = make_context_chunk(content="beta")
    # Orthogonal vectors -> cosine similarity 0.0, below the default threshold.
    provider, _ = _make_provider([[1.0, 0.0], [0.0, 1.0]])

    result = await provider.compress(CompressionRequest(chunks=[first, second]))

    assert result.chunks == [first, second]
    assert result.statistics.removed_chunks == 0


async def test_compress_honors_a_custom_similarity_threshold() -> None:
    first = make_context_chunk(content="alpha")
    second = make_context_chunk(content="beta")
    # Same moderately-similar pair (cosine similarity 0.6) both times.
    vectors = [[1.0, 0.0], [0.6, 0.8]]

    lenient_provider, _ = _make_provider(vectors, similarity_threshold=0.9)
    lenient_result = await lenient_provider.compress(
        CompressionRequest(chunks=[first, second]),
    )
    assert lenient_result.chunks == [first, second]

    strict_provider, _ = _make_provider(vectors, similarity_threshold=0.5)
    strict_result = await strict_provider.compress(
        CompressionRequest(chunks=[first, second]),
    )
    assert strict_result.chunks == [first]


async def test_compress_reports_accurate_statistics() -> None:
    a = make_context_chunk(content="a")
    duplicate_of_a = make_context_chunk(content="a again")
    b = make_context_chunk(content="b")
    # a/duplicate_of_a identical (removed); b orthogonal to a (kept).
    provider, _ = _make_provider([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])

    result = await provider.compress(CompressionRequest(chunks=[a, duplicate_of_a, b]))

    assert result.chunks == [a, b]
    assert result.statistics.original_chunks == 3
    assert result.statistics.compressed_chunks == 2
    assert result.statistics.removed_chunks == 1


async def test_compress_encodes_every_chunks_content_text() -> None:
    first = make_context_chunk(content="alpha")
    second = make_context_chunk(content="beta")
    provider, model = _make_provider([[1.0, 0.0], [0.0, 1.0]])

    await provider.compress(CompressionRequest(chunks=[first, second]))

    model.encode.assert_called_once()
    assert model.encode.call_args.args[0] == ["alpha", "beta"]
