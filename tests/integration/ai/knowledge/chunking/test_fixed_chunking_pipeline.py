"""
Component integration test for the Chunking Platform.

This test exercises the complete chunking pipeline:

ProcessedDocument
        ↓
ChunkingService
        ↓
ChunkingRegistry
        ↓
FixedChunkingProvider
        ↓
list[Chunk]

No providers are mocked.

The objective is to verify that the platform is correctly wired together
and produces deterministic chunks with the expected metadata.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.factory import create_chunking_service
from app.ai.knowledge.chunking.providers.fixed import FixedChunkingProvider
from app.ai.knowledge.processing.enums import (
    DocumentFormat,
    ParserType,
)
from app.ai.knowledge.processing.models import (
    DocumentMetadata,
    DocumentStatistics,
    ProcessedDocument,
)


@pytest.mark.asyncio
async def test_fixed_chunking_pipeline() -> None:
    """
    Verify the Fixed Chunking pipeline end-to-end.
    """

    service = create_chunking_service()

    document = ProcessedDocument(
        document_id=uuid4(),
        filename="research-paper.pdf",
        format=DocumentFormat.PDF,
        parser=ParserType.DOCLING,
        metadata=DocumentMetadata(
            title="ResearchMind Test Document",
            source="research-paper.pdf",
        ),
        statistics=DocumentStatistics(),
        raw_text=(
            "Artificial Intelligence is transforming modern software engineering. "
            "Large Language Models enable new ways of interacting with information. "
            "ResearchMind is a production-grade AI knowledge platform built to "
            "experiment with chunking, embeddings, retrieval, reranking, and "
            "agentic workflows. "
        )
        * 40,
        markdown="",
        blocks=[],
    )

    chunks = await service.chunk(
        document=document,
        strategy=ChunkingStrategy.FIXED,
    )

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------

    assert chunks

    assert len(chunks) > 1

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------

    for index, chunk in enumerate(chunks):
        assert chunk.index == index

    # ------------------------------------------------------------------
    # Total chunks
    # ------------------------------------------------------------------

    for chunk in chunks:
        assert chunk.total_chunks == len(chunks)

    # ------------------------------------------------------------------
    # Chunk IDs
    # ------------------------------------------------------------------

    chunk_ids = {chunk.id for chunk in chunks}

    assert len(chunk_ids) == len(chunks)

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    for chunk in chunks:
        assert chunk.provenance.document_id == document.document_id
        assert chunk.provenance.filename == document.filename
        assert chunk.provenance.parser == ParserType.DOCLING.value

    # ------------------------------------------------------------------
    # Experiment metadata
    # ------------------------------------------------------------------

    for chunk in chunks:
        assert chunk.experiment.strategy == ChunkingStrategy.FIXED
        assert chunk.experiment.strategy_version == "1.0"
        assert chunk.experiment.configuration_fingerprint

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    for chunk in chunks:
        assert chunk.statistics.character_count > 0
        assert chunk.statistics.word_count > 0
        assert chunk.statistics.estimated_token_count > 0

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    for chunk in chunks:
        assert chunk.content.text

    # ------------------------------------------------------------------
    # Verify overlap
    # ------------------------------------------------------------------

    provider = service._registry.get(ChunkingStrategy.FIXED)

    assert isinstance(provider, FixedChunkingProvider)

    overlap = provider.config.chunk_overlap

    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert previous.content.text[-overlap:] == current.content.text[:overlap]
