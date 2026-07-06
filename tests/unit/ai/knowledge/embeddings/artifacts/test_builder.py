"""
Unit tests for EmbeddingArtifactBuilder.

Covers:
- Aggregate statistics are computed correctly across embeddings
- Document/chunking metadata are derived from the source ChunkArtifact
- Execution metadata is derived from the first embedding
- Building from an empty embedding collection raises ValueError
"""

from __future__ import annotations

import uuid

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
from app.ai.knowledge.embeddings.artifacts.builder import EmbeddingArtifactBuilder
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.factory import EmbeddingFactory
from app.ai.knowledge.embeddings.models import Embedding

_DOCUMENT_ID = uuid.uuid4()


def _make_chunk(text: str) -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        index=0,
        total_chunks=1,
        content=ChunkContent(text=text, content_type=ChunkContentType.TEXT),
        structure=ChunkStructure(),
        statistics=ChunkStatistics(
            character_count=len(text),
            word_count=len(text.split()),
            estimated_token_count=len(text.split()),
        ),
        provenance=ChunkProvenance(
            document_id=_DOCUMENT_ID,
            filename="test.pdf",
            parser="docling",
            parser_version="1.0",
        ),
        experiment=ChunkExperiment(
            strategy=ChunkingStrategy.FIXED,
            strategy_version="1.0",
            configuration_fingerprint="chunk-fingerprint",
        ),
    )


def _make_chunk_artifact(chunks: list[Chunk]) -> ChunkArtifact:
    return ChunkArtifact(
        document=ChunkArtifactDocument(
            document_id=_DOCUMENT_ID,
            filename="test.pdf",
            parser="docling",
            parser_version="1.0",
        ),
        strategy=ChunkArtifactStrategy(
            strategy=ChunkingStrategy.FIXED,
            strategy_version="1.0",
            configuration_fingerprint="chunk-fingerprint",
        ),
        statistics=ChunkArtifactStatistics(),
        chunks=chunks,
    )


def _make_embedding(chunk: Chunk, vector: list[float]) -> Embedding:
    return EmbeddingFactory.from_vector(
        chunk=chunk,
        vector=vector,
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        model="all-MiniLM-L6-v2",
        provider_version="1.0",
        configuration_fingerprint="embedding-fingerprint",
    )


def test_build_aggregates_statistics_across_embeddings() -> None:
    chunks = [_make_chunk("hello world"), _make_chunk("goodbye world")]
    chunk_artifact = _make_chunk_artifact(chunks)
    embeddings = [
        _make_embedding(chunks[0], [0.1, 0.2]),
        _make_embedding(chunks[1], [0.3, 0.4]),
    ]

    artifact = EmbeddingArtifactBuilder().build(
        chunk_artifact=chunk_artifact,
        embeddings=embeddings,
    )

    assert artifact.statistics.total_embeddings == 2
    assert artifact.statistics.dimensions == 2
    assert artifact.statistics.total_characters == sum(
        e.statistics.character_count for e in embeddings
    )
    assert artifact.statistics.total_words == sum(e.statistics.word_count for e in embeddings)
    assert artifact.statistics.total_estimated_tokens == sum(
        e.statistics.estimated_token_count for e in embeddings
    )
    assert artifact.embeddings == embeddings


def test_build_derives_document_and_chunking_metadata_from_chunk_artifact() -> None:
    chunks = [_make_chunk("hello world")]
    chunk_artifact = _make_chunk_artifact(chunks)
    embeddings = [_make_embedding(chunks[0], [0.1, 0.2])]

    artifact = EmbeddingArtifactBuilder().build(
        chunk_artifact=chunk_artifact,
        embeddings=embeddings,
    )

    assert artifact.document.document_id == chunk_artifact.document.document_id
    assert artifact.document.filename == chunk_artifact.document.filename
    assert artifact.document.parser == chunk_artifact.document.parser

    assert artifact.chunking.strategy == chunk_artifact.strategy.strategy
    assert artifact.chunking.strategy_version == chunk_artifact.strategy.strategy_version
    assert (
        artifact.chunking.configuration_fingerprint
        == chunk_artifact.strategy.configuration_fingerprint
    )


def test_build_derives_execution_metadata_from_first_embedding() -> None:
    chunks = [_make_chunk("hello world")]
    chunk_artifact = _make_chunk_artifact(chunks)
    embeddings = [_make_embedding(chunks[0], [0.1, 0.2])]
    first_embedding = embeddings[0]

    artifact = EmbeddingArtifactBuilder().build(
        chunk_artifact=chunk_artifact,
        embeddings=embeddings,
    )

    assert artifact.execution.provider == first_embedding.experiment.provider
    assert artifact.execution.provider_version == first_embedding.experiment.provider_version
    assert artifact.execution.model == first_embedding.provider.model
    assert (
        artifact.execution.configuration_fingerprint
        == first_embedding.experiment.configuration_fingerprint
    )


def test_build_raises_value_error_for_empty_embeddings() -> None:
    chunk_artifact = _make_chunk_artifact([_make_chunk("hello world")])

    with pytest.raises(ValueError, match="empty embedding collection"):
        EmbeddingArtifactBuilder().build(
            chunk_artifact=chunk_artifact,
            embeddings=[],
        )
