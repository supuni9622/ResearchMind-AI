"""
Unit tests for EmbeddingArtifactWriter.

Covers:
- The storage key layout embeds owner, document, provider, and artifact id
- The serialized payload and content type passed to storage
- Storage failures propagate to the caller
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.embeddings.artifacts.models import (
    EmbeddingArtifact,
    EmbeddingArtifactChunking,
    EmbeddingArtifactDocument,
    EmbeddingArtifactExecution,
    EmbeddingArtifactStatistics,
)
from app.ai.knowledge.embeddings.artifacts.writer import EmbeddingArtifactWriter
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.infrastructure.storage.exceptions import StorageUploadError

_DOCUMENT_ID = uuid.uuid4()


def _make_artifact() -> EmbeddingArtifact:
    return EmbeddingArtifact(
        document=EmbeddingArtifactDocument(
            document_id=_DOCUMENT_ID,
            filename="test.pdf",
            parser="docling",
        ),
        chunking=EmbeddingArtifactChunking(
            strategy=ChunkingStrategy.FIXED,
            strategy_version="1.0",
            configuration_fingerprint="chunk-fingerprint",
        ),
        execution=EmbeddingArtifactExecution(
            provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
            provider_version="1.0",
            model="all-MiniLM-L6-v2",
            configuration_fingerprint="fingerprint",
        ),
        statistics=EmbeddingArtifactStatistics(total_embeddings=1, dimensions=384),
    )


async def test_write_uploads_to_the_expected_key() -> None:
    storage = AsyncMock()
    artifact = _make_artifact()
    writer = EmbeddingArtifactWriter(storage)

    await writer.write(owner_id="owner-1", artifact=artifact)

    storage.upload.assert_awaited_once()
    call = storage.upload.await_args

    expected_key = (
        f"documents/owner-1/{_DOCUMENT_ID}/embeddings/"
        f"{EmbeddingProvider.SENTENCE_TRANSFORMERS.value}/{artifact.artifact_id}/embeddings.json"
    )
    assert call.kwargs["key"] == expected_key
    assert call.kwargs["content_type"] == "application/json"


async def test_write_uploads_the_serialized_artifact() -> None:
    storage = AsyncMock()
    artifact = _make_artifact()
    writer = EmbeddingArtifactWriter(storage)

    await writer.write(owner_id="owner-1", artifact=artifact)

    uploaded_file = storage.upload.await_args.kwargs["file"]
    payload = uploaded_file.read().decode("utf-8")

    assert str(artifact.artifact_id) in payload
    assert "all-MiniLM-L6-v2" in payload


async def test_write_propagates_storage_errors() -> None:
    storage = AsyncMock()
    storage.upload = AsyncMock(side_effect=StorageUploadError("bucket unreachable"))
    artifact = _make_artifact()
    writer = EmbeddingArtifactWriter(storage)

    with pytest.raises(StorageUploadError):
        await writer.write(owner_id="owner-1", artifact=artifact)
