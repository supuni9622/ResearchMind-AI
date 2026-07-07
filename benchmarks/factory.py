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

from app.ai.knowledge.chunking.artifacts.builder import (
    ChunkArtifactBuilder,
)
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.factory import (
    create_chunking_registry,
    create_chunking_service,
)
from app.ai.knowledge.embeddings.create import create_embedding_registry

from benchmarks.chunking.benchmark import ChunkingBenchmark
from benchmarks.common.dataset_loader import DatasetLoader
from benchmarks.embeddings.benchmark import EmbeddingBenchmark
from benchmarks.registry import BenchmarkRegistry


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

    #
    # Future benchmarks
    #
    # registry.register(
    #     RetrievalBenchmark(...)
    # )
    #
    # registry.register(
    #     PipelineBenchmark(...)
    # )

    return registry
