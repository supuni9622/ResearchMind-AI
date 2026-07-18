"""
Integration tests for the Hierarchical (Parent/Child) Chunking pipeline.

These tests verify that the complete Chunking Platform works
end-to-end using the HierarchicalChunkingProvider.

Pipeline:

ProcessedDocument
    ↓
ChunkingService
    ↓
HierarchicalChunkingProvider
    ↓
Parent Documents -> Child Chunks
    ↓
ChunkArtifactBuilder
    ↓
ChunkArtifact
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.config import HierarchicalChunkingConfig
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.providers.hierarchical import (
    HierarchicalChunkingProvider,
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
    paragraph = (
        "Retrieval-Augmented Generation improves factual accuracy by grounding "
        "large language model outputs in retrieved evidence. "
    )

    return ProcessedDocument(
        document_id=uuid4(),
        filename="research-paper.pdf",
        format=DocumentFormat.PDF,
        parser=ParserType.DOCLING,
        metadata=DocumentMetadata(
            title="Research Paper",
        ),
        statistics=DocumentStatistics(),
        raw_text=(paragraph * 30 + "\n\n" + paragraph * 30 + "\n\n" + paragraph * 30),
        markdown="",
        blocks=[],
    )


@pytest.fixture
def chunking_service() -> ChunkingService:
    registry = ChunkingRegistry()

    registry.register(
        HierarchicalChunkingProvider(
            HierarchicalChunkingConfig(
                parent_chunk_size=800,
                parent_chunk_overlap=0,
                child_chunk_size=150,
                child_chunk_overlap=0,
            )
        )
    )

    return ChunkingService(registry=registry)


@pytest.mark.asyncio
async def test_hierarchical_chunking_pipeline(
    processed_document: ProcessedDocument,
    chunking_service: ChunkingService,
) -> None:
    """
    Verify the complete Parent/Child hierarchical chunking pipeline.
    """

    chunks = await chunking_service.chunk(
        document=processed_document,
        strategy=ChunkingStrategy.HIERARCHICAL,
    )

    assert len(chunks) > 0

    parents = [chunk for chunk in chunks if chunk.experiment.additional_metadata.get("is_parent")]
    children = [
        chunk for chunk in chunks if not chunk.experiment.additional_metadata.get("is_parent")
    ]

    # ---------------------------------------------------------
    # Parent Documents
    # ---------------------------------------------------------

    assert len(parents) > 1

    for chunk in parents:
        assert chunk.structure.hierarchy_level == 0
        assert chunk.structure.parent_chunk_id is None
        assert chunk.experiment.strategy == ChunkingStrategy.HIERARCHICAL

    # ---------------------------------------------------------
    # Child Chunks
    # ---------------------------------------------------------

    assert len(children) > len(parents)

    parent_ids = {parent.id for parent in parents}

    for chunk in children:
        assert chunk.structure.hierarchy_level == 1
        assert chunk.structure.parent_chunk_id in parent_ids
        assert chunk.content.text

    # Every parent has at least one child pointing back at it.
    referenced_parent_ids = {chunk.structure.parent_chunk_id for chunk in children}
    assert referenced_parent_ids == parent_ids

    # ---------------------------------------------------------
    # Retrieve Child -> Expand Parent
    # ---------------------------------------------------------

    parents_by_id = {parent.id: parent for parent in parents}

    for chunk in children:
        assert chunk.structure.parent_chunk_id is not None
        parent = parents_by_id[chunk.structure.parent_chunk_id]
        assert chunk.content.text in parent.content.text

    # ---------------------------------------------------------
    # Artifact persists both parents and children
    # ---------------------------------------------------------

    artifact = ChunkArtifactBuilder().build(chunks)

    assert artifact.statistics.total_chunks == len(chunks)

    serialized = artifact.model_dump()

    assert len(serialized["chunks"]) == len(chunks)
