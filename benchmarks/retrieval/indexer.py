"""
Retrieval benchmark indexer.

Chunks and embeds (dense + sparse) the benchmark corpus and upserts it
into a dedicated Qdrant collection so retrieval candidates can be
evaluated against a real vector index.

The benchmark intentionally does not reuse IndexingService, since that
service always targets the production collection configured via
settings.qdrant_collection_name. The indexer instead builds canonical
VectorStoreRecord objects directly and drives VectorStoreService, so
benchmark runs never touch production data.

The target collection is dropped and recreated on every run so results
stay reproducible against the current state of the benchmark corpus.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.service import ChunkingService
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry
from app.ai.knowledge.indexing.providers.fastembed import (
    FastEmbedSparseEmbeddingProvider,
)
from app.ai.knowledge.processing.models import ProcessedDocument
from app.ai.knowledge.vectorstores.enums import (
    VectorDistanceMetric,
    VectorStoreProvider,
)
from app.ai.knowledge.vectorstores.models import (
    CollectionDefinition,
    VectorPayload,
    VectorStoreRecord,
)
from app.ai.knowledge.vectorstores.service import VectorStoreService
from qdrant_client import AsyncQdrantClient


class BenchmarkRetrievalIndexer:
    """
    Builds a dedicated, reproducible Qdrant collection for retrieval
    benchmarking.
    """

    def __init__(
        self,
        *,
        chunking_service: ChunkingService,
        chunking_strategy: ChunkingStrategy,
        chunk_artifact_builder: ChunkArtifactBuilder,
        embedding_registry: EmbeddingRegistry,
        sparse_embedding_provider: FastEmbedSparseEmbeddingProvider,
        vectorstore_service: VectorStoreService,
        qdrant_client: AsyncQdrantClient,
        collection_name: str,
    ) -> None:
        self._chunking_service = chunking_service
        self._chunking_strategy = chunking_strategy
        self._chunk_artifact_builder = chunk_artifact_builder
        self._embedding_registry = embedding_registry
        self._sparse_embedding_provider = sparse_embedding_provider
        self._vectorstore_service = vectorstore_service
        self._qdrant_client = qdrant_client
        self._collection_name = collection_name

    async def index(
        self,
        documents: list[ProcessedDocument],
        *,
        owner_ids_by_document_id: dict[UUID, str] | None = None,
    ) -> int:
        """
        Chunk, embed, and upsert the benchmark corpus.

        Args:
            documents:
                Benchmark documents to index.

            owner_ids_by_document_id:
                Optional per-document owner_id override, keyed by
                ProcessedDocument.document_id. Documents missing from
                the mapping (or when the mapping itself is omitted) fall
                back to the shared "benchmark" owner, preserving the
                default single-tenant behaviour used by RetrievalBenchmark.

        Returns:
            Number of vector records indexed.
        """

        dense_provider = self._embedding_registry.get(
            EmbeddingProvider.VOYAGE_AI,
        )

        records: list[VectorStoreRecord] = []
        dimensions = 0

        for document in documents:
            owner_id = (owner_ids_by_document_id or {}).get(
                document.document_id,
                "benchmark",
            )

            chunks = await self._chunking_service.chunk(
                document=document,
                strategy=self._chunking_strategy,
            )
            artifact = self._chunk_artifact_builder.build(chunks)

            chunks_by_id = {chunk.id: chunk for chunk in artifact.chunks}

            embeddings = await dense_provider.embed(artifact)

            sparse_vectors = await self._sparse_embedding_provider.embed(
                [chunk.content.text for chunk in artifact.chunks],
            )
            sparse_by_chunk_id = {
                chunk.id: sparse_vector
                for chunk, sparse_vector in zip(
                    artifact.chunks,
                    sparse_vectors,
                    strict=True,
                )
            }

            for embedding in embeddings:
                chunk = chunks_by_id[embedding.provenance.chunk_id]
                dimensions = embedding.vector.dimensions

                records.append(
                    VectorStoreRecord(
                        id=embedding.id,
                        vector=embedding.vector.values,
                        sparse_vector=sparse_by_chunk_id[chunk.id],
                        payload=VectorPayload(
                            document_id=embedding.provenance.document_id,
                            chunk_id=embedding.provenance.chunk_id,
                            filename=embedding.provenance.filename,
                            content=chunk.content.text,
                            owner_id=owner_id,
                            chunk_index=chunk.index,
                        ),
                    )
                )

        if not records:
            raise ValueError("No vector records were produced for the benchmark corpus.")

        await self._recreate_collection(
            dimensions=dimensions,
        )

        await self._vectorstore_service.upsert(
            provider=VectorStoreProvider.QDRANT,
            collection_name=self._collection_name,
            records=records,
        )

        return len(records)

    async def _recreate_collection(
        self,
        *,
        dimensions: int,
    ) -> None:
        """
        Drop the benchmark collection if it exists and recreate it, so
        every benchmark run starts from a clean, reproducible index.
        """

        exists = await self._vectorstore_service.collection_exists(
            provider=VectorStoreProvider.QDRANT,
            collection_name=self._collection_name,
        )

        if exists:
            await self._qdrant_client.delete_collection(
                self._collection_name,
            )

        await self._vectorstore_service.create_collection(
            provider=VectorStoreProvider.QDRANT,
            definition=CollectionDefinition(
                name=self._collection_name,
                provider=VectorStoreProvider.QDRANT,
                dimensions=dimensions,
                distance_metric=VectorDistanceMetric.DOT,
            ),
        )
