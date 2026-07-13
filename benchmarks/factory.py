"""
Benchmark platform factory.

Assembles the Engineering Benchmark Platform by constructing benchmark
implementations, registering them, and returning a configured
BenchmarkRegistry.

This module is the composition root for the Benchmark Platform.

Adding a new benchmark should require only constructing it here and
registering it with the BenchmarkRegistry.
"""

from __future__ import annotations

from app.ai.knowledge.cache.query_embeddings.null import (
    NullQueryEmbeddingCache,
)
from app.ai.knowledge.chunking.artifacts.builder import (
    ChunkArtifactBuilder,
)
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.factory import (
    create_chunking_registry,
    create_chunking_service,
)
from app.ai.knowledge.embeddings.create import create_embedding_registry
from app.ai.knowledge.indexing.create import (
    create_sparse_embedding_provider,
)
from app.ai.knowledge.retrieval.config import QdrantRetrievalConfig
from app.ai.knowledge.retrieval.providers.qdrant import (
    QdrantRetrievalProvider,
)
from app.ai.knowledge.retrieval.query.dense_service import (
    QueryEmbeddingService,
)
from app.ai.knowledge.retrieval.query.sparse_service import (
    SparseQueryEmbeddingService,
)
from app.ai.knowledge.vectorstores.create import (
    create_qdrant_client,
    create_vectorstore_service,
)

from benchmarks.chunking.benchmark import ChunkingBenchmark
from benchmarks.common.dataset_loader import DatasetLoader
from benchmarks.embeddings.benchmark import EmbeddingBenchmark
from benchmarks.registry import BenchmarkRegistry
from benchmarks.retrieval.benchmark import (
    BENCHMARK_COLLECTION_NAME,
    RetrievalBenchmark,
)
from benchmarks.retrieval.indexer import BenchmarkRetrievalIndexer


def create_benchmark_registry() -> BenchmarkRegistry:
    """
    Create a fully configured BenchmarkRegistry.
    """

    registry = BenchmarkRegistry()

    dataset_loader = DatasetLoader()

    registry.register(
        ChunkingBenchmark(
            registry=create_chunking_registry(),
            artifact_builder=ChunkArtifactBuilder(),
            dataset_loader=dataset_loader,
        )
    )

    registry.register(
        EmbeddingBenchmark(
            registry=create_embedding_registry(),
            chunking_service=create_chunking_service(),
            chunking_strategy=ChunkingStrategy.RECURSIVE,
            chunk_artifact_builder=ChunkArtifactBuilder(),
            dataset_loader=dataset_loader,
        )
    )

    qdrant_client = create_qdrant_client()
    embedding_registry = create_embedding_registry()
    sparse_embedding_provider = create_sparse_embedding_provider()

    registry.register(
        RetrievalBenchmark(
            dataset_loader=dataset_loader,
            indexer=BenchmarkRetrievalIndexer(
                chunking_service=create_chunking_service(),
                chunking_strategy=ChunkingStrategy.RECURSIVE,
                chunk_artifact_builder=ChunkArtifactBuilder(),
                embedding_registry=embedding_registry,
                sparse_embedding_provider=sparse_embedding_provider,
                vectorstore_service=create_vectorstore_service(),
                qdrant_client=qdrant_client,
                collection_name=BENCHMARK_COLLECTION_NAME,
            ),
            retrieval_provider=QdrantRetrievalProvider(
                client=qdrant_client,
                config=QdrantRetrievalConfig(
                    collection_name=BENCHMARK_COLLECTION_NAME,
                ),
            ),
            query_embedding_service=QueryEmbeddingService(
                registry=embedding_registry,
                cache=NullQueryEmbeddingCache(),
            ),
            sparse_query_embedding_service=SparseQueryEmbeddingService(
                provider=sparse_embedding_provider,
            ),
        )
    )

    #
    # Future benchmarks
    #
    # registry.register(
    #     PipelineBenchmark(...)
    # )

    return registry
