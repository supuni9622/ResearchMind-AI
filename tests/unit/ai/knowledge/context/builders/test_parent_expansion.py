"""
Unit tests for ParentExpansionService.

Covers:
- Empty input returns immediately without touching the artifact reader
- A chunk missing chunk_artifact_id/chunking_strategy metadata is left
  unenriched and excluded from any reader call
- A chunk with artifact metadata but no parent_chunk_id triggers a
  reader load (chunks are grouped by artifact, not filtered ahead of
  time) but stays unenriched
- A resolvable parent_chunk_id enriches parent_content/page_numbers/
  heading/heading_path from the loaded artifact's matching chunk
- An unresolvable parent_chunk_id (not present in the loaded artifact)
  does not raise and leaves the chunk unenriched
- Multiple chunks sharing the same (owner_id, document_id, strategy,
  artifact_id) group trigger exactly one reader.load() call
- Chunks from distinct groups each trigger their own reader.load() call
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from app.ai.knowledge.chunking.artifacts.models import (
    ChunkArtifact,
    ChunkArtifactDocument,
    ChunkArtifactStatistics,
    ChunkArtifactStrategy,
)
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.models import (
    Chunk,
    ChunkContent,
    ChunkExperiment,
    ChunkProvenance,
    ChunkStatistics,
    ChunkStructure,
)
from app.ai.knowledge.context.builders.parent_expansion import ParentExpansionService

from tests.unit.ai.knowledge.context.factories import make_context_chunk


def _make_parent_chunk(*, chunk_id: uuid.UUID, document_id: uuid.UUID) -> Chunk:
    return Chunk(
        id=chunk_id,
        index=0,
        total_chunks=1,
        content=ChunkContent(text="parent chunk text"),
        structure=ChunkStructure(
            heading="Introduction",
            heading_path=["Introduction"],
            page_numbers=[1, 2],
        ),
        statistics=ChunkStatistics(),
        provenance=ChunkProvenance(document_id=document_id, filename="paper.pdf", parser="docling"),
        experiment=ChunkExperiment(
            strategy=ChunkingStrategy.RECURSIVE, configuration_fingerprint="fp"
        ),
    )


def _make_artifact(*, document_id: uuid.UUID, parent_chunks: list[Chunk]) -> ChunkArtifact:
    return ChunkArtifact(
        document=ChunkArtifactDocument(
            document_id=document_id, filename="paper.pdf", parser="docling"
        ),
        strategy=ChunkArtifactStrategy(
            strategy=ChunkingStrategy.RECURSIVE,
            strategy_version="1.0",
            configuration_fingerprint="fp",
        ),
        statistics=ChunkArtifactStatistics(total_chunks=len(parent_chunks)),
        chunks=parent_chunks,
    )


def _make_reader(artifact: ChunkArtifact | None = None) -> AsyncMock:
    reader = AsyncMock()
    if artifact is not None:
        reader.load = AsyncMock(return_value=artifact)
    return reader


async def test_expand_with_empty_chunks_never_calls_the_reader() -> None:
    reader = _make_reader()
    service = ParentExpansionService(artifact_reader=reader)

    result = await service.expand([])

    assert result == []
    reader.load.assert_not_called()


async def test_expand_skips_chunks_missing_artifact_metadata() -> None:
    reader = _make_reader()
    service = ParentExpansionService(artifact_reader=reader)
    chunk = make_context_chunk(metadata={})

    result = await service.expand([chunk])

    assert result[0].parent_content is None
    reader.load.assert_not_called()


async def test_expand_loads_the_artifact_even_without_a_parent_chunk_id() -> None:
    document_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    artifact = _make_artifact(document_id=document_id, parent_chunks=[])
    reader = _make_reader(artifact)
    service = ParentExpansionService(artifact_reader=reader)
    chunk = make_context_chunk(
        document_id=document_id,
        owner_id="owner-1",
        metadata={
            "chunk_artifact_id": str(artifact_id),
            "chunking_strategy": "recursive",
        },
    )

    result = await service.expand([chunk])

    reader.load.assert_awaited_once_with(
        owner_id="owner-1",
        document_id=document_id,
        strategy="recursive",
        artifact_id=artifact_id,
    )
    assert result[0].parent_content is None


async def test_expand_enriches_chunk_from_resolvable_parent() -> None:
    document_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    parent_chunk_id = uuid.uuid4()
    parent = _make_parent_chunk(chunk_id=parent_chunk_id, document_id=document_id)
    artifact = _make_artifact(document_id=document_id, parent_chunks=[parent])
    reader = _make_reader(artifact)
    service = ParentExpansionService(artifact_reader=reader)
    chunk = make_context_chunk(
        document_id=document_id,
        owner_id="owner-1",
        parent_chunk_id=parent_chunk_id,
        metadata={
            "chunk_artifact_id": str(artifact_id),
            "chunking_strategy": "recursive",
        },
    )

    result = await service.expand([chunk])

    enriched = result[0]
    assert enriched.parent_content == "parent chunk text"
    assert enriched.page_numbers == [1, 2]
    assert enriched.heading == "Introduction"
    assert enriched.heading_path == ["Introduction"]


async def test_expand_leaves_chunk_unenriched_when_parent_id_not_found() -> None:
    document_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    artifact = _make_artifact(document_id=document_id, parent_chunks=[])
    reader = _make_reader(artifact)
    service = ParentExpansionService(artifact_reader=reader)
    chunk = make_context_chunk(
        document_id=document_id,
        owner_id="owner-1",
        parent_chunk_id=uuid.uuid4(),
        metadata={
            "chunk_artifact_id": str(artifact_id),
            "chunking_strategy": "recursive",
        },
    )

    result = await service.expand([chunk])

    assert result[0].parent_content is None


async def test_expand_loads_once_per_shared_artifact_group() -> None:
    document_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    parent_chunk_id = uuid.uuid4()
    parent = _make_parent_chunk(chunk_id=parent_chunk_id, document_id=document_id)
    artifact = _make_artifact(document_id=document_id, parent_chunks=[parent])
    reader = _make_reader(artifact)
    service = ParentExpansionService(artifact_reader=reader)

    metadata = {"chunk_artifact_id": str(artifact_id), "chunking_strategy": "recursive"}
    first = make_context_chunk(
        document_id=document_id,
        owner_id="owner-1",
        parent_chunk_id=parent_chunk_id,
        metadata=metadata,
    )
    second = make_context_chunk(
        document_id=document_id,
        owner_id="owner-1",
        parent_chunk_id=parent_chunk_id,
        metadata=metadata,
    )

    result = await service.expand([first, second])

    reader.load.assert_awaited_once()
    assert all(chunk.parent_content == "parent chunk text" for chunk in result)


async def test_expand_loads_separately_for_distinct_groups() -> None:
    document_a = uuid.uuid4()
    document_b = uuid.uuid4()
    artifact_a_id = uuid.uuid4()
    artifact_b_id = uuid.uuid4()

    reader = AsyncMock()
    reader.load = AsyncMock(
        side_effect=lambda **kwargs: _make_artifact(
            document_id=kwargs["document_id"], parent_chunks=[]
        )
    )
    service = ParentExpansionService(artifact_reader=reader)

    chunk_a = make_context_chunk(
        document_id=document_a,
        owner_id="owner-1",
        metadata={"chunk_artifact_id": str(artifact_a_id), "chunking_strategy": "recursive"},
    )
    chunk_b = make_context_chunk(
        document_id=document_b,
        owner_id="owner-1",
        metadata={"chunk_artifact_id": str(artifact_b_id), "chunking_strategy": "markdown"},
    )

    await service.expand([chunk_a, chunk_b])

    assert reader.load.await_count == 2
