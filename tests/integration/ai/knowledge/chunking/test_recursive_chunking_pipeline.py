"""
Integration tests for the Recursive Chunking pipeline.

These tests verify that the complete Chunking Platform works
end-to-end using the RecursiveChunkingProvider.

Pipeline:

ProcessedDocument
    ↓
ChunkingService
    ↓
RecursiveChunkingProvider
    ↓
ChunkArtifactBuilder
    ↓
ChunkArtifact
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.config import RecursiveChunkingConfig
from app.ai.knowledge.chunking.enums import (
    ChunkContentType,
    ChunkingStrategy,
)
from app.ai.knowledge.chunking.providers.recursive import (
    RecursiveChunkingProvider,
)
from app.ai.knowledge.chunking.registry import ChunkingRegistry
from app.ai.knowledge.chunking.service import ChunkingService
from app.ai.knowledge.processing.enums import (
    DocumentFormat,
    ParserType,
)
from app.ai.knowledge.processing.models import (
    DocumentMetadata,
    DocumentStatistics,
    ProcessedDocument,
)


@pytest.fixture
def processed_document() -> ProcessedDocument:
    """
    Canonical processed document used throughout the integration tests.
    """

    return ProcessedDocument(
        document_id=uuid4(),
        filename="research-paper.pdf",
        format=DocumentFormat.PDF,
        parser=ParserType.DOCLING,
        metadata=DocumentMetadata(
            title="Research Paper",
        ),
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


@pytest.fixture
def chunking_service() -> ChunkingService:
    """
    ChunkingService configured with the Recursive provider.
    """

    registry = ChunkingRegistry()

    registry.register(
        RecursiveChunkingProvider(
            RecursiveChunkingConfig(
                chunk_size=100,
                chunk_overlap=20,
            )
        )
    )

    return ChunkingService(
        registry=registry,
    )


@pytest.mark.asyncio
async def test_recursive_chunking_pipeline(
    processed_document: ProcessedDocument,
    chunking_service: ChunkingService,
) -> None:
    """
    Verify the complete recursive chunking pipeline.
    """

    chunks = await chunking_service.chunk(
        document=processed_document,
        strategy=ChunkingStrategy.RECURSIVE,
    )

    # ---------------------------------------------------------
    # Provider
    # ---------------------------------------------------------

    assert len(chunks) > 0

    # ---------------------------------------------------------
    # Canonical Chunk Model
    # ---------------------------------------------------------

    for index, chunk in enumerate(chunks):
        assert chunk.index == index
        assert chunk.total_chunks == len(chunks)

        assert chunk.content.text
        assert chunk.content.content_type == ChunkContentType.TEXT

        assert chunk.statistics.character_count > 0
        assert chunk.statistics.word_count > 0
        assert chunk.statistics.estimated_token_count > 0

        assert chunk.provenance.document_id == processed_document.document_id

        assert chunk.provenance.filename == processed_document.filename

        assert chunk.provenance.parser == ParserType.DOCLING

        assert chunk.experiment.strategy == ChunkingStrategy.RECURSIVE

    # ---------------------------------------------------------
    # Artifact
    # ---------------------------------------------------------

    artifact = ChunkArtifactBuilder().build(chunks)

    assert artifact.document.document_id == processed_document.document_id

    assert artifact.document.filename == processed_document.filename

    assert artifact.strategy.strategy == ChunkingStrategy.RECURSIVE

    assert artifact.statistics.total_chunks == len(chunks)

    assert artifact.statistics.total_characters > 0

    assert artifact.statistics.total_words > 0

    assert artifact.statistics.total_estimated_tokens > 0

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    serialized = artifact.model_dump()

    assert serialized["document"]["document_id"]

    assert serialized["strategy"]["strategy"] == "recursive"

    assert serialized["statistics"]["total_chunks"] == len(chunks)

    assert len(serialized["chunks"]) == len(chunks)
