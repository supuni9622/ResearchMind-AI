"""
Integration tests for the Sentence Transformers embedding pipeline.

These tests verify that the complete Embedding Platform works
end-to-end using the real SentenceTransformerEmbeddingProvider.

Pipeline:

ChunkArtifact
    ↓
EmbeddingService
    ↓
SentenceTransformerEmbeddingProvider
    ↓
EmbeddingArtifactBuilder
    ↓
EmbeddingArtifact
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.config import RecursiveChunkingConfig
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.providers.recursive import RecursiveChunkingProvider
from app.ai.knowledge.chunking.registry import ChunkingRegistry
from app.ai.knowledge.chunking.service import ChunkingService
from app.ai.knowledge.embeddings.artifacts.builder import EmbeddingArtifactBuilder
from app.ai.knowledge.embeddings.create import create_embedding_service
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.processing.enums import DocumentFormat, ParserType
from app.ai.knowledge.processing.models import (
    DocumentMetadata,
    DocumentStatistics,
    ProcessedDocument,
)


@pytest.fixture
def processed_document() -> ProcessedDocument:
    return ProcessedDocument(
        document_id=uuid4(),
        filename="research-paper.pdf",
        format=DocumentFormat.PDF,
        parser=ParserType.DOCLING,
        metadata=DocumentMetadata(title="Research Paper"),
        statistics=DocumentStatistics(),
        raw_text=(
            "Artificial Intelligence\n\n"
            "Artificial intelligence is transforming industries.\n\n"
            "Machine learning enables systems to improve automatically.\n\n"
            "Large Language Models are capable of reasoning over text.\n\n"
            "Retrieval-Augmented Generation improves factual accuracy."
        ),
        markdown=(
            "# Artificial Intelligence\n\n"
            "Artificial intelligence is transforming industries.\n\n"
            "Machine learning enables systems to improve automatically.\n\n"
            "Large Language Models are capable of reasoning over text.\n\n"
            "Retrieval-Augmented Generation improves factual accuracy."
        ),
        blocks=[],
    )


@pytest.mark.asyncio
async def test_sentence_transformers_embedding_pipeline(
    processed_document: ProcessedDocument,
) -> None:
    """
    Verify the complete embedding pipeline against real chunks, using the
    real SentenceTransformerEmbeddingProvider.
    """

    chunking_registry = ChunkingRegistry()
    chunking_registry.register(
        RecursiveChunkingProvider(
            RecursiveChunkingConfig(chunk_size=100, chunk_overlap=20),
        )
    )
    chunks = await ChunkingService(registry=chunking_registry).chunk(
        document=processed_document,
        strategy=ChunkingStrategy.RECURSIVE,
    )
    chunk_artifact = ChunkArtifactBuilder().build(chunks)

    embedding_service = create_embedding_service()

    embeddings = await embedding_service.embed(
        artifact=chunk_artifact,
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
    )

    # ---------------------------------------------------------
    # Canonical Embedding Model
    # ---------------------------------------------------------

    assert len(embeddings) == len(chunks)

    dimensions = embeddings[0].vector.dimensions
    assert dimensions > 0

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        assert embedding.provenance.document_id == processed_document.document_id
        assert embedding.provenance.chunk_id == chunk.id

        assert embedding.provider.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS
        assert embedding.provider.model == "all-MiniLM-L6-v2"

        assert embedding.vector.dimensions == dimensions
        assert len(embedding.vector.values) == dimensions

    # ---------------------------------------------------------
    # Artifact
    # ---------------------------------------------------------

    artifact = EmbeddingArtifactBuilder().build(
        chunk_artifact=chunk_artifact,
        embeddings=embeddings,
    )

    assert artifact.document.document_id == processed_document.document_id
    assert artifact.execution.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS
    assert artifact.statistics.total_embeddings == len(embeddings)
    assert artifact.statistics.dimensions == dimensions

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    serialized = artifact.model_dump()

    assert serialized["execution"]["provider"] == "sentence_transformers"
    assert len(serialized["embeddings"]) == len(embeddings)
