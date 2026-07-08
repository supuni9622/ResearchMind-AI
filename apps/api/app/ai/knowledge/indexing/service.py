"""
Indexing Platform service.

The IndexingService orchestrates indexing operations.

Responsibilities

- Validate indexing requests
- Transform embedding artifacts into index records
- Delegate indexing to indexing technologies
- Build indexing artifacts
- Persist indexing artifacts

Current MVP

- Vector Store

Future

- BM25
- Knowledge Graph
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.ai.knowledge.indexing.artifacts.builder import (
    IndexingArtifactBuilder,
)
from app.ai.knowledge.indexing.artifacts.models import (
    IndexingArtifactExecution,
)
from app.ai.knowledge.indexing.artifacts.writer import (
    IndexingArtifactWriter,
)
from app.ai.knowledge.indexing.enums import (
    IndexStatus,
)
from app.ai.knowledge.indexing.exceptions import (
    InvalidIndexingRequestError,
)
from app.ai.knowledge.indexing.interfaces import (
    IndexingServiceInterface,
)
from app.ai.knowledge.indexing.models import (
    IndexingExecution,
    IndexingRequest,
    IndexingResult,
)
from app.ai.knowledge.indexing.providers.fastembed import (
    FastEmbedSparseEmbeddingProvider,
)
from app.ai.knowledge.vectorstores.enums import (
    VectorStoreProvider,
)
from app.ai.knowledge.vectorstores.models import (
    CollectionDefinition,
    IndexStatistics,
    VectorPayload,
    VectorStoreRecord,
)
from app.ai.knowledge.vectorstores.service import (
    VectorStoreService,
)
from app.core.settings import settings


class IndexingService(IndexingServiceInterface):
    """
    Orchestrates knowledge indexing.

    The service is responsible for coordinating one or more indexing
    technologies while remaining independent from concrete provider
    implementations.
    """

    def __init__(
        self,
        vectorstore_service: VectorStoreService,
        artifact_writer: IndexingArtifactWriter,
        sparse_embedding_provider: FastEmbedSparseEmbeddingProvider,
    ) -> None:
        self._vectorstore = vectorstore_service
        self._artifact_writer = artifact_writer
        self._sparse_embedding_provider = sparse_embedding_provider

    async def index(
        self,
        request: IndexingRequest,
    ) -> IndexingResult:
        """
        Index an embedding artifact.

        Current MVP

        - Vector Store

        Future

        - Vector Store
        - BM25
        - Knowledge Graph
        """

        self._validate(request)

        started_at = datetime.now(UTC)

        collection = self._build_collection_definition(
            request,
        )

        records = await self._build_vector_records(
            request,
        )

        exists = await self._vectorstore.collection_exists(
            provider=VectorStoreProvider.QDRANT,
            collection_name=collection.name,
        )

        if not exists:
            await self._vectorstore.create_collection(
                provider=VectorStoreProvider.QDRANT,
                definition=collection,
            )

        await self._vectorstore.upsert(
            provider=VectorStoreProvider.QDRANT,
            collection_name=collection.name,
            records=records,
        )

        statistics = self._build_statistics(
            records=records,
            started_at=started_at,
        )

        completed_at = datetime.now(UTC)

        execution = IndexingExecution(
            operation=request.operation,
            status=IndexStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
        )

        result = IndexingResult(
            execution=execution,
            vector_collection=collection,
            vector_statistics=statistics,
            successful_indexes=["vector"],
            failed_indexes=[],
        )

        artifact = IndexingArtifactBuilder.build(
            execution=IndexingArtifactExecution(
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=statistics.duration_ms,
                status=IndexStatus.COMPLETED,
            ),
            result=result,
        )

        await self._artifact_writer.write(
            owner_id=request.owner_id,
            document_id=str(request.embedding_artifact.document.document_id),
            artifact=artifact,
        )

        return result

    async def reindex(
        self,
        request: IndexingRequest,
    ) -> IndexingResult:
        """
        Rebuild all configured indexes for an embedding artifact.

        Current MVP

        - Vector Store

        Future

        - BM25
        - Knowledge Graph
        """

        await self.delete(request)

        return await self.index(request)

    def _validate(
        self,
        request: IndexingRequest,
    ) -> None:
        """
        Validate an indexing request.
        """

        if not request.embedding_artifact.embeddings:
            raise InvalidIndexingRequestError("Embedding artifact contains no embeddings.")

        if not request.chunk_artifact.chunks:
            raise InvalidIndexingRequestError("Chunk artifact contains no chunks.")

    def _build_collection_definition(
        self,
        request: IndexingRequest,
    ) -> CollectionDefinition:
        """
        Build the target vector collection definition.
        """

        artifact = request.embedding_artifact

        dimensions = artifact.statistics.dimensions

        return CollectionDefinition(
            name=settings.qdrant_collection_name,
            provider=VectorStoreProvider.QDRANT,
            dimensions=dimensions,
            distance_metric=artifact.execution.recommended_distance_metric,
        )

    async def _build_vector_records(
        self,
        request: IndexingRequest,
    ) -> list[VectorStoreRecord]:
        """
        Transform canonical embeddings into vector store records.

        Each dense embedding is paired with a sparse SPLADE vector
        generated from its source chunk text, enabling Qdrant native
        hybrid retrieval (see ADR-019).
        """

        artifact = request.embedding_artifact

        chunks_by_id = {chunk.id: chunk for chunk in request.chunk_artifact.chunks}

        sparse_vectors = await self._sparse_embedding_provider.embed(
            [
                chunks_by_id[embedding.provenance.chunk_id].content.text
                for embedding in artifact.embeddings
            ]
        )

        records: list[VectorStoreRecord] = []

        for embedding, sparse_vector in zip(
            artifact.embeddings,
            sparse_vectors,
            strict=True,
        ):
            chunk = chunks_by_id[embedding.provenance.chunk_id]

            records.append(
                VectorStoreRecord(
                    id=embedding.id,
                    vector=embedding.vector.values,
                    sparse_vector=sparse_vector,
                    payload=VectorPayload(
                        document_id=embedding.provenance.document_id,
                        chunk_id=embedding.provenance.chunk_id,
                        filename=embedding.provenance.filename,
                        owner_id=request.owner_id,
                        chunk_index=chunk.index,
                        language=None,
                        additional_metadata={},
                    ),
                )
            )

        return records

    def _build_statistics(
        self,
        *,
        records: list[VectorStoreRecord],
        started_at: datetime,
    ) -> IndexStatistics:
        """
        Build indexing statistics.
        """

        duration_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000

        return IndexStatistics(
            indexed_vectors=len(records),
            failed_vectors=0,
            indexed_sparse_vectors=sum(1 for record in records if record.sparse_vector is not None),
            batch_size=len(records),
            duration_ms=duration_ms,
        )

    async def delete(
        self,
        request: IndexingRequest,
    ) -> IndexingResult:
        """
        Remove a document from all configured indexes.

        Current MVP

        - Vector Store

        Future

        - BM25
        - Knowledge Graph
        """

        self._validate(request)

        started_at = datetime.now(UTC)

        collection = self._build_collection_definition(
            request,
        )

        document_id = str(request.embedding_artifact.document.document_id)

        await self._vectorstore.delete_document(
            provider=VectorStoreProvider.QDRANT,
            collection_name=collection.name,
            document_id=document_id,
        )

        completed_at = datetime.now(UTC)

        statistics = IndexStatistics(
            indexed_vectors=0,
            failed_vectors=0,
            batch_size=0,
            duration_ms=(completed_at - started_at).total_seconds() * 1000,
        )

        execution = IndexingExecution(
            operation=request.operation,
            status=IndexStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
        )

        result = IndexingResult(
            execution=execution,
            vector_collection=collection,
            vector_statistics=statistics,
            successful_indexes=["vector"],
            failed_indexes=[],
        )

        artifact = IndexingArtifactBuilder.build(
            execution=IndexingArtifactExecution(
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=statistics.duration_ms,
                status=IndexStatus.COMPLETED,
            ),
            result=result,
        )

        await self._artifact_writer.write(
            owner_id=request.owner_id,
            document_id=document_id,
            artifact=artifact,
        )

        return result
