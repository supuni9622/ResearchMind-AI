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
from app.ai.knowledge.reranking.create import (
    create_reranking_registry,
)
from app.ai.knowledge.retrieval.config import QdrantRetrievalConfig
from app.ai.knowledge.retrieval.fusion.service import (
    RetrievalFusionService,
)
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
from app.ai.runtime.generation.create import (
    create_generation_registry,
)
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.service import (
    GenerationService,
)
from app.core.settings import settings

from benchmarks.chunking.benchmark import ChunkingBenchmark
from benchmarks.common.dataset_loader import DatasetLoader
from benchmarks.embeddings.benchmark import EmbeddingBenchmark
from benchmarks.generation.abstention_benchmark import AbstentionBenchmark
from benchmarks.generation.benchmark import GenerationBenchmark
from benchmarks.generation.golden_set_benchmark import GoldenSetBenchmark
from benchmarks.generation.production_failures_benchmark import (
    ProductionFailuresBenchmark,
)
from benchmarks.generation.schema_validity_benchmark import SchemaValidityBenchmark
from benchmarks.ingestion.benchmark import IngestionFidelityBenchmark
from benchmarks.registry import BenchmarkRegistry
from benchmarks.reranking.benchmark import (
    BENCHMARK_COLLECTION_NAME as RERANKING_COLLECTION_NAME,
)
from benchmarks.reranking.benchmark import (
    RerankingBenchmark,
)
from benchmarks.retrieval.benchmark import (
    BENCHMARK_COLLECTION_NAME,
    RetrievalBenchmark,
)
from benchmarks.retrieval.indexer import BenchmarkRetrievalIndexer
from benchmarks.retrieval.metadata_filtering_benchmark import (
    BENCHMARK_COLLECTION_NAME as METADATA_FILTERING_COLLECTION_NAME,
)
from benchmarks.retrieval.metadata_filtering_benchmark import (
    MetadataFilteringBenchmark,
)


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
        IngestionFidelityBenchmark(),
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
            fusion_service=RetrievalFusionService(),
        )
    )

    registry.register(
        MetadataFilteringBenchmark(
            dataset_loader=dataset_loader,
            indexer=BenchmarkRetrievalIndexer(
                chunking_service=create_chunking_service(),
                chunking_strategy=ChunkingStrategy.RECURSIVE,
                chunk_artifact_builder=ChunkArtifactBuilder(),
                embedding_registry=embedding_registry,
                sparse_embedding_provider=sparse_embedding_provider,
                vectorstore_service=create_vectorstore_service(),
                qdrant_client=qdrant_client,
                collection_name=METADATA_FILTERING_COLLECTION_NAME,
            ),
            retrieval_provider=QdrantRetrievalProvider(
                client=qdrant_client,
                config=QdrantRetrievalConfig(
                    collection_name=METADATA_FILTERING_COLLECTION_NAME,
                ),
            ),
            query_embedding_service=QueryEmbeddingService(
                registry=embedding_registry,
                cache=NullQueryEmbeddingCache(),
            ),
            sparse_query_embedding_service=SparseQueryEmbeddingService(
                provider=sparse_embedding_provider,
            ),
            fusion_service=RetrievalFusionService(),
        )
    )

    registry.register(
        RerankingBenchmark(
            dataset_loader=dataset_loader,
            indexer=BenchmarkRetrievalIndexer(
                chunking_service=create_chunking_service(),
                chunking_strategy=ChunkingStrategy.RECURSIVE,
                chunk_artifact_builder=ChunkArtifactBuilder(),
                embedding_registry=embedding_registry,
                sparse_embedding_provider=sparse_embedding_provider,
                vectorstore_service=create_vectorstore_service(),
                qdrant_client=qdrant_client,
                collection_name=RERANKING_COLLECTION_NAME,
            ),
            retrieval_provider=QdrantRetrievalProvider(
                client=qdrant_client,
                config=QdrantRetrievalConfig(
                    collection_name=RERANKING_COLLECTION_NAME,
                ),
            ),
            query_embedding_service=QueryEmbeddingService(
                registry=embedding_registry,
                cache=NullQueryEmbeddingCache(),
            ),
            sparse_query_embedding_service=SparseQueryEmbeddingService(
                provider=sparse_embedding_provider,
            ),
            fusion_service=RetrievalFusionService(),
            reranking_registry=create_reranking_registry(),
        )
    )

    generation_registry = create_generation_registry()

    registry.register(
        GenerationBenchmark(
            registry=generation_registry,
            generation_service=GenerationService(
                registry=generation_registry,
            ),
        )
    )

    #
    # GoldenSetGeneration/ProductionFailuresRegression both need a real
    # Ragas judge, which needs OPENAI_API_KEY (see
    # `ragas_judge.build_openai_ragas_judge()`, which raises without
    # one). Registered only when a key is configured, so
    # `create_benchmark_registry()` -- called unconditionally by every
    # benchmark run, including ones that need no LLM at all (Ingestion
    # Fidelity, Chunking) -- never fails to construct the registry itself
    # just because these two optional benchmarks can't be built yet.
    #
    if settings.openai_api_key:
        from app.ai.runtime.generation.orchestration.create import (
            create_generation_runtime,
        )
        from app.ai.runtime.research.planner.service import ResearchPlanner

        from benchmarks.generation.abstention_judge import build_abstention_judge
        from benchmarks.generation.ragas_judge import build_openai_ragas_judge
        from benchmarks.generation.rubric_judge import build_rubric_judge

        # Same fallback chain, same judge instances for both -- building a
        # judge is a cheap local client-wrapper construction (no network
        # call), and one real judge identity should score both datasets
        # for the same run rather than two separately constructed (but
        # behaviorally identical) instances.
        judge = build_openai_ragas_judge()
        # E16 -- deliberately its own fixed-cheap-model client, not routed
        # through `generation_service`/`provider_fallback_chain` below,
        # which would use whatever OPENAI_MODEL is configured for real
        # answers (see rubric_judge.py's own module docstring for why
        # that would be a real cost problem, not just a style choice).
        rubric_judge = build_rubric_judge()
        # Same reasoning as rubric_judge above, its own fixed-cheap-model
        # client -- feeds abstention_pass_rate (AbstentionBenchmark) and
        # ProductionFailuresBenchmark's abstention_failure category.
        abstention_judge = build_abstention_judge()
        provider_fallback_chain = [GenerationProvider.OPENAI, GenerationProvider.CLAUDE]

        registry.register(
            GoldenSetBenchmark(
                generation_service=GenerationService(
                    registry=generation_registry,
                ),
                judge=judge,
                # OpenAI first, falling back to Claude per-example on
                # failure -- not the full registry (which includes Groq,
                # whose free-tier daily token limit a real 115-example
                # run has already hit mid-pass; see golden_set_benchmark
                # .py's own module docstring).
                providers=provider_fallback_chain,
                rubric_judge=rubric_judge,
            )
        )

        registry.register(
            ProductionFailuresBenchmark(
                generation_service=GenerationService(
                    registry=generation_registry,
                ),
                judge=judge,
                providers=provider_fallback_chain,
                rubric_judge=rubric_judge,
                abstention_judge=abstention_judge,
            )
        )

        registry.register(
            AbstentionBenchmark(
                generation_service=GenerationService(
                    registry=generation_registry,
                ),
                abstention_judge=abstention_judge,
                providers=provider_fallback_chain,
            )
        )

        registry.register(
            SchemaValidityBenchmark(
                planner=ResearchPlanner(generation_runtime=create_generation_runtime()),
            )
        )

    #
    # Future benchmarks
    #
    # registry.register(
    #     PipelineBenchmark(...)
    # )

    return registry
