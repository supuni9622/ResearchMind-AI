"""
Unit tests for ChunkArtifactReader.

Covers:
- The storage key is built exactly as
  documents/{owner_id}/{document_id}/chunking/{strategy}/{artifact_id}/chunks.json
- A valid downloaded payload is parsed into a canonical ChunkArtifact
- Storage errors propagate untouched (the reader does no error wrapping)
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
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
from app.ai.knowledge.context.artifacts.reader import ChunkArtifactReader
from app.infrastructure.storage.exceptions import StorageDownloadError


def _make_artifact(*, document_id: uuid.UUID, chunk_id: uuid.UUID) -> ChunkArtifact:
    chunk = Chunk(
        id=chunk_id,
        index=0,
        total_chunks=1,
        content=ChunkContent(text="parent chunk text"),
        structure=ChunkStructure(heading="Intro", heading_path=["Intro"], page_numbers=[1]),
        statistics=ChunkStatistics(),
        provenance=ChunkProvenance(
            document_id=document_id,
            filename="paper.pdf",
            parser="docling",
        ),
        experiment=ChunkExperiment(
            strategy=ChunkingStrategy.RECURSIVE,
            configuration_fingerprint="fp",
        ),
    )

    return ChunkArtifact(
        document=ChunkArtifactDocument(
            document_id=document_id,
            filename="paper.pdf",
            parser="docling",
        ),
        strategy=ChunkArtifactStrategy(
            strategy=ChunkingStrategy.RECURSIVE,
            strategy_version="1.0",
            configuration_fingerprint="fp",
        ),
        statistics=ChunkArtifactStatistics(total_chunks=1),
        chunks=[chunk],
    )


def _make_storage(payload: bytes | None = None) -> AsyncMock:
    storage = AsyncMock()
    if payload is not None:
        storage.download = AsyncMock(return_value=payload)
    return storage


async def test_load_builds_the_expected_storage_key() -> None:
    document_id = uuid.uuid4()
    artifact = _make_artifact(document_id=document_id, chunk_id=uuid.uuid4())
    storage = _make_storage(artifact.model_dump_json().encode("utf-8"))
    reader = ChunkArtifactReader(storage=storage)
    artifact_id = uuid.uuid4()

    await reader.load(
        owner_id="owner-1",
        document_id=document_id,
        strategy="recursive",
        artifact_id=artifact_id,
    )

    storage.download.assert_awaited_once_with(
        key=f"documents/owner-1/{document_id}/chunking/recursive/{artifact_id}/chunks.json",
    )


async def test_load_parses_downloaded_payload_into_canonical_artifact() -> None:
    document_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    artifact = _make_artifact(document_id=document_id, chunk_id=chunk_id)
    storage = _make_storage(artifact.model_dump_json().encode("utf-8"))
    reader = ChunkArtifactReader(storage=storage)

    result = await reader.load(
        owner_id="owner-1",
        document_id=document_id,
        strategy="recursive",
        artifact_id=uuid.uuid4(),
    )

    assert isinstance(result, ChunkArtifact)
    assert len(result.chunks) == 1
    assert result.chunks[0].id == chunk_id
    assert result.chunks[0].content.text == "parent chunk text"


async def test_load_propagates_storage_errors_untouched() -> None:
    storage = AsyncMock()
    storage.download = AsyncMock(side_effect=StorageDownloadError("not found"))
    reader = ChunkArtifactReader(storage=storage)

    with pytest.raises(StorageDownloadError):
        await reader.load(
            owner_id="owner-1",
            document_id=uuid.uuid4(),
            strategy="recursive",
            artifact_id=uuid.uuid4(),
        )
