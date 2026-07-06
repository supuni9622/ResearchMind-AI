"""
Unit tests for EmbeddingFactory.

Covers:
- Provenance, statistics, and provider metadata are copied from the
  source chunk
- Vector dimensions are derived from the generated vector
- Optional model_version defaults to None when not supplied
"""

from __future__ import annotations

import uuid

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
from app.ai.knowledge.embeddings.factory import EmbeddingFactory

_DOCUMENT_ID = uuid.uuid4()


def _make_chunk() -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        index=0,
        total_chunks=1,
        content=ChunkContent(text="hello world", content_type=ChunkContentType.TEXT),
        structure=ChunkStructure(),
        statistics=ChunkStatistics(
            character_count=11,
            word_count=2,
            estimated_token_count=3,
        ),
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


def test_from_vector_maps_provenance_and_statistics_from_chunk() -> None:
    chunk = _make_chunk()

    embedding = EmbeddingFactory.from_vector(
        chunk=chunk,
        vector=[0.1, 0.2, 0.3],
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        model="all-MiniLM-L6-v2",
        provider_version="1.0",
        configuration_fingerprint="config-fingerprint",
    )

    assert embedding.provenance.document_id == chunk.provenance.document_id
    assert embedding.provenance.chunk_id == chunk.id
    assert embedding.provenance.filename == chunk.provenance.filename

    assert embedding.statistics.character_count == chunk.statistics.character_count
    assert embedding.statistics.word_count == chunk.statistics.word_count
    assert embedding.statistics.estimated_token_count == chunk.statistics.estimated_token_count

    assert embedding.provider.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS
    assert embedding.provider.model == "all-MiniLM-L6-v2"
    assert embedding.provider.model_version is None

    assert embedding.experiment.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS
    assert embedding.experiment.provider_version == "1.0"
    assert embedding.experiment.configuration_fingerprint == "config-fingerprint"


def test_from_vector_derives_dimensions_from_vector_length() -> None:
    chunk = _make_chunk()

    embedding = EmbeddingFactory.from_vector(
        chunk=chunk,
        vector=[0.1, 0.2, 0.3, 0.4],
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        model="all-MiniLM-L6-v2",
        provider_version="1.0",
        configuration_fingerprint="config-fingerprint",
    )

    assert embedding.vector.values == [0.1, 0.2, 0.3, 0.4]
    assert embedding.vector.dimensions == 4


def test_from_vector_accepts_explicit_model_version() -> None:
    chunk = _make_chunk()

    embedding = EmbeddingFactory.from_vector(
        chunk=chunk,
        vector=[0.1],
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        model="all-MiniLM-L6-v2",
        provider_version="1.0",
        configuration_fingerprint="config-fingerprint",
        model_version="v2",
    )

    assert embedding.provider.model_version == "v2"
