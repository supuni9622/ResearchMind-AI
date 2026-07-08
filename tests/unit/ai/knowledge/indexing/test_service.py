"""
Unit tests for IndexingService.

Covers:
- Dense embeddings are paired with sparse vectors by chunk_id (not list
  position), and each record's payload.chunk_index reflects the chunk's
  real position rather than a hardcoded 0
- Collection creation is skipped when the collection already exists
- Collection definition is derived from the embedding artifact
- The built records are upserted and the resulting statistics count both
  dense and sparse vectors
- The indexing artifact is persisted under the correct owner/document
- Validation failures for an empty embedding artifact or empty chunk
  artifact
- delete() removes the document from the vector store and persists an
  artifact; reindex() performs delete() then index()
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock
from uuid import UUID

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
from app.ai.knowledge.embeddings.artifacts.models import (
    EmbeddingArtifact,
    EmbeddingArtifactChunking,
    EmbeddingArtifactDocument,
    EmbeddingArtifactExecution,
    EmbeddingArtifactStatistics,
)
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.factory import EmbeddingFactory
from app.ai.knowledge.embeddings.models import Embedding
from app.ai.knowledge.indexing.exceptions import InvalidIndexingRequestError
from app.ai.knowledge.indexing.models import IndexingRequest
from app.ai.knowledge.indexing.service import IndexingService
from app.ai.knowledge.vectorstores.enums import VectorDistanceMetric, VectorStoreProvider
from app.ai.knowledge.vectorstores.models import SparseVector
from app.core.settings import settings

_OWNER_ID = "owner-1"


def _make_chunk(*, text: str, index: int, document_id: UUID) -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        index=index,
        total_chunks=2,
        content=ChunkContent(text=text, content_type=ChunkContentType.TEXT),
        structure=ChunkStructure(),
        statistics=ChunkStatistics(character_count=len(text)),
        provenance=ChunkProvenance(
            document_id=document_id,
            filename="test.pdf",
            parser="docling",
        ),
        experiment=ChunkExperiment(
            strategy=ChunkingStrategy.MARKDOWN,
            configuration_fingerprint="chunk-fingerprint",
        ),
    )


def _make_chunk_artifact(*, document_id: UUID, chunks: list[Chunk]) -> ChunkArtifact:
    return ChunkArtifact(
        document=ChunkArtifactDocument(
            document_id=document_id,
            filename="test.pdf",
            parser="docling",
        ),
        strategy=ChunkArtifactStrategy(
            strategy=ChunkingStrategy.MARKDOWN,
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
        provider=EmbeddingProvider.VOYAGE_AI,
        model="voyage-3-lite",
        provider_version="1.0",
        configuration_fingerprint="embedding-fingerprint",
    )


def _make_embedding_artifact(
    *,
    chunk_artifact: ChunkArtifact,
    embeddings: list[Embedding],
) -> EmbeddingArtifact:
    return EmbeddingArtifact(
        document=EmbeddingArtifactDocument(
            document_id=chunk_artifact.document.document_id,
            filename=chunk_artifact.document.filename,
            parser=chunk_artifact.document.parser,
        ),
        chunking=EmbeddingArtifactChunking(
            strategy=chunk_artifact.strategy.strategy,
            strategy_version=chunk_artifact.strategy.strategy_version,
            configuration_fingerprint=chunk_artifact.strategy.configuration_fingerprint,
        ),
        execution=EmbeddingArtifactExecution(
            provider=EmbeddingProvider.VOYAGE_AI,
            provider_version="1.0",
            model="voyage-3-lite",
            recommended_distance_metric=VectorDistanceMetric.DOT,
            configuration_fingerprint="embedding-fingerprint",
        ),
        statistics=EmbeddingArtifactStatistics(
            total_embeddings=len(embeddings),
            dimensions=embeddings[0].vector.dimensions if embeddings else 0,
        ),
        embeddings=embeddings,
    )


def _make_services() -> tuple[IndexingService, AsyncMock, AsyncMock, AsyncMock]:
    vectorstore_service = AsyncMock()
    vectorstore_service.collection_exists = AsyncMock(return_value=False)

    artifact_writer = AsyncMock()

    sparse_provider = AsyncMock()
    # Default: one deterministic sparse vector per input text, order preserved.
    sparse_provider.embed = AsyncMock(
        side_effect=lambda texts: [
            SparseVector(indices=[i], values=[0.1]) for i in range(len(texts))
        ]
    )

    service = IndexingService(
        vectorstore_service=vectorstore_service,
        artifact_writer=artifact_writer,
        sparse_embedding_provider=sparse_provider,
    )
    return service, vectorstore_service, artifact_writer, sparse_provider


def _single_chunk_setup() -> tuple[ChunkArtifact, EmbeddingArtifact, UUID]:
    document_id = uuid.uuid4()
    chunk = _make_chunk(text="alpha", index=0, document_id=document_id)
    chunk_artifact = _make_chunk_artifact(document_id=document_id, chunks=[chunk])
    embedding = _make_embedding(chunk, [0.1, 0.2])
    embedding_artifact = _make_embedding_artifact(
        chunk_artifact=chunk_artifact,
        embeddings=[embedding],
    )
    return chunk_artifact, embedding_artifact, document_id


# ---------------------------------------------------------------------------
# index() — dense/sparse record building
# ---------------------------------------------------------------------------


async def test_index_pairs_embeddings_to_chunks_by_chunk_id_not_position() -> None:
    """
    Embeddings are matched to chunk text via chunk_id, and payload
    chunk_index reflects the chunk's real position — regression coverage
    for a bug where chunk_index was hardcoded to 0 for every record.
    """

    document_id = uuid.uuid4()
    chunk_a = _make_chunk(text="alpha", index=0, document_id=document_id)
    chunk_b = _make_chunk(text="beta", index=1, document_id=document_id)
    chunk_artifact = _make_chunk_artifact(document_id=document_id, chunks=[chunk_a, chunk_b])

    # Embeddings deliberately built in the reverse of chunk order.
    embedding_b = _make_embedding(chunk_b, [0.1, 0.2])
    embedding_a = _make_embedding(chunk_a, [0.3, 0.4])
    embedding_artifact = _make_embedding_artifact(
        chunk_artifact=chunk_artifact,
        embeddings=[embedding_b, embedding_a],
    )

    service, vectorstore_service, _artifact_writer, sparse_provider = _make_services()

    sparse_for_beta = SparseVector(indices=[1], values=[0.9])
    sparse_for_alpha = SparseVector(indices=[2], values=[0.8])
    sparse_provider.embed = AsyncMock(return_value=[sparse_for_beta, sparse_for_alpha])

    request = IndexingRequest(
        owner_id=_OWNER_ID,
        embedding_artifact=embedding_artifact,
        chunk_artifact=chunk_artifact,
    )

    result = await service.index(request)

    # Sparse provider receives chunk text in embeddings order (beta, alpha).
    sparse_provider.embed.assert_awaited_once_with(["beta", "alpha"])

    records = vectorstore_service.upsert.await_args.kwargs["records"]
    assert len(records) == 2

    record_for_b = next(r for r in records if r.id == embedding_b.id)
    record_for_a = next(r for r in records if r.id == embedding_a.id)

    assert record_for_b.payload.chunk_index == 1
    assert record_for_a.payload.chunk_index == 0

    assert record_for_b.sparse_vector == sparse_for_beta
    assert record_for_a.sparse_vector == sparse_for_alpha

    assert result.vector_statistics is not None
    assert result.vector_statistics.indexed_vectors == 2
    assert result.vector_statistics.indexed_sparse_vectors == 2
    assert result.successful_indexes == ["vector"]


async def test_index_creates_collection_when_missing() -> None:
    chunk_artifact, embedding_artifact, _ = _single_chunk_setup()
    service, vectorstore_service, _artifact_writer, _sparse_provider = _make_services()
    vectorstore_service.collection_exists = AsyncMock(return_value=False)

    await service.index(
        IndexingRequest(
            owner_id=_OWNER_ID,
            embedding_artifact=embedding_artifact,
            chunk_artifact=chunk_artifact,
        )
    )

    vectorstore_service.create_collection.assert_awaited_once()


async def test_index_skips_collection_creation_when_it_already_exists() -> None:
    chunk_artifact, embedding_artifact, _ = _single_chunk_setup()
    service, vectorstore_service, _artifact_writer, _sparse_provider = _make_services()
    vectorstore_service.collection_exists = AsyncMock(return_value=True)

    await service.index(
        IndexingRequest(
            owner_id=_OWNER_ID,
            embedding_artifact=embedding_artifact,
            chunk_artifact=chunk_artifact,
        )
    )

    vectorstore_service.create_collection.assert_not_awaited()


async def test_index_builds_collection_definition_from_embedding_artifact() -> None:
    chunk_artifact, embedding_artifact, _ = _single_chunk_setup()
    service, *_rest = _make_services()

    result = await service.index(
        IndexingRequest(
            owner_id=_OWNER_ID,
            embedding_artifact=embedding_artifact,
            chunk_artifact=chunk_artifact,
        )
    )

    assert result.vector_collection is not None
    assert result.vector_collection.name == settings.qdrant_collection_name
    assert result.vector_collection.provider == VectorStoreProvider.QDRANT
    assert result.vector_collection.dimensions == 2
    assert result.vector_collection.distance_metric == VectorDistanceMetric.DOT


async def test_index_persists_artifact_with_owner_and_document_id() -> None:
    chunk_artifact, embedding_artifact, document_id = _single_chunk_setup()
    service, _vectorstore_service, artifact_writer, _sparse_provider = _make_services()

    await service.index(
        IndexingRequest(
            owner_id=_OWNER_ID,
            embedding_artifact=embedding_artifact,
            chunk_artifact=chunk_artifact,
        )
    )

    artifact_writer.write.assert_awaited_once()
    call_kwargs = artifact_writer.write.await_args.kwargs
    assert call_kwargs["owner_id"] == _OWNER_ID
    assert call_kwargs["document_id"] == str(document_id)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


async def test_index_raises_when_embedding_artifact_has_no_embeddings() -> None:
    chunk_artifact, embedding_artifact, _ = _single_chunk_setup()
    empty_embedding_artifact = embedding_artifact.model_copy(
        update={"embeddings": []},
    )
    service, *_rest = _make_services()

    with pytest.raises(InvalidIndexingRequestError, match="no embeddings"):
        await service.index(
            IndexingRequest(
                owner_id=_OWNER_ID,
                embedding_artifact=empty_embedding_artifact,
                chunk_artifact=chunk_artifact,
            )
        )


async def test_index_raises_when_chunk_artifact_has_no_chunks() -> None:
    chunk_artifact, embedding_artifact, document_id = _single_chunk_setup()
    empty_chunk_artifact = _make_chunk_artifact(document_id=document_id, chunks=[])
    service, *_rest = _make_services()

    with pytest.raises(InvalidIndexingRequestError, match="no chunks"):
        await service.index(
            IndexingRequest(
                owner_id=_OWNER_ID,
                embedding_artifact=embedding_artifact,
                chunk_artifact=empty_chunk_artifact,
            )
        )


# ---------------------------------------------------------------------------
# delete() / reindex()
# ---------------------------------------------------------------------------


async def test_delete_removes_document_and_persists_artifact() -> None:
    chunk_artifact, embedding_artifact, document_id = _single_chunk_setup()
    service, vectorstore_service, artifact_writer, _sparse_provider = _make_services()

    result = await service.delete(
        IndexingRequest(
            owner_id=_OWNER_ID,
            embedding_artifact=embedding_artifact,
            chunk_artifact=chunk_artifact,
        )
    )

    vectorstore_service.delete_document.assert_awaited_once_with(
        provider=VectorStoreProvider.QDRANT,
        collection_name=settings.qdrant_collection_name,
        document_id=str(document_id),
    )
    assert result.vector_statistics is not None
    assert result.vector_statistics.indexed_vectors == 0
    artifact_writer.write.assert_awaited_once()


async def test_reindex_deletes_then_reindexes() -> None:
    chunk_artifact, embedding_artifact, _ = _single_chunk_setup()
    service, vectorstore_service, artifact_writer, _sparse_provider = _make_services()

    await service.reindex(
        IndexingRequest(
            owner_id=_OWNER_ID,
            embedding_artifact=embedding_artifact,
            chunk_artifact=chunk_artifact,
        )
    )

    vectorstore_service.delete_document.assert_awaited_once()
    vectorstore_service.upsert.assert_awaited_once()
    assert artifact_writer.write.await_count == 2
