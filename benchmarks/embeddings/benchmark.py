"""
Embedding benchmark.

Benchmarks every registered embedding provider against the same set of
canonical chunks and produces a canonical BenchmarkReport.

Chunks are generated once per document using a fixed chunking strategy
so that every embedding provider is evaluated against identical input,
keeping the comparison fair.

The benchmark intentionally operates directly on canonical
ProcessedDocument and ChunkArtifact models without requiring S3,
workers, or queues.
"""

from __future__ import annotations

from pathlib import Path

from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.service import ChunkingService
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry

from benchmarks.common.dataset_loader import DatasetLoader
from benchmarks.common.timer import Timer
from benchmarks.interfaces.benchmark import Benchmark
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkReport,
)


class EmbeddingBenchmark(Benchmark):
    """
    Engineering benchmark for the Embedding Platform.
    """

    def __init__(
        self,
        *,
        registry: EmbeddingRegistry,
        chunking_service: ChunkingService,
        chunking_strategy: ChunkingStrategy,
        chunk_artifact_builder: ChunkArtifactBuilder,
        dataset_loader: DatasetLoader,
    ) -> None:
        self._registry = registry
        self._chunking_service = chunking_service
        self._chunking_strategy = chunking_strategy
        self._chunk_artifact_builder = chunk_artifact_builder
        self._dataset_loader = dataset_loader

    @property
    def name(self) -> str:
        return "Embeddings"

    async def run(
        self,
        dataset_path: Path,
    ) -> BenchmarkReport:
        """
        Execute the embedding benchmark.

        Args:
            dataset_path:
                Root benchmark dataset directory.

        Returns:
            Canonical benchmark report.
        """

        documents = self._dataset_loader.load_documents(
            dataset_path,
        )

        chunk_artifacts: list[ChunkArtifact] = []

        for document in documents:
            chunks = await self._chunking_service.chunk(
                document=document,
                strategy=self._chunking_strategy,
            )
            chunk_artifacts.append(self._chunk_artifact_builder.build(chunks))

        candidates: dict[str, BenchmarkCandidate] = {}

        for provider in self._registry.providers.values():
            total_documents = 0
            total_chunks = 0
            total_embeddings = 0
            dimensions = 0
            error: str | None = None

            with Timer() as timer:
                try:
                    for chunk_artifact in chunk_artifacts:
                        embeddings = await provider.embed(chunk_artifact)

                        total_documents += 1
                        total_chunks += len(chunk_artifact.chunks)
                        total_embeddings += len(embeddings)

                        if embeddings:
                            dimensions = embeddings[0].vector.dimensions
                except Exception as exc:  # noqa: BLE001
                    # Embedding providers call external, rate-limited SDKs.
                    # One provider failing (e.g. Voyage AI throttling) should
                    # not prevent the report from covering the others.
                    error = str(exc)

            duration_seconds = timer.elapsed_seconds

            average_latency_ms = (
                (duration_seconds / total_embeddings) * 1000 if total_embeddings else 0
            )

            throughput = total_embeddings / duration_seconds if duration_seconds else 0

            notes: dict[str, str] = {"model": provider.model}

            if error is not None:
                notes["error"] = error

            candidates[provider.provider.value] = BenchmarkCandidate(
                name=provider.provider.value,
                version=provider.version,
                metrics={
                    "documents": total_documents,
                    "total_chunks": total_chunks,
                    "total_embeddings": total_embeddings,
                    "dimensions": dimensions,
                    "duration_seconds": round(duration_seconds, 4),
                    "average_latency_ms": round(average_latency_ms, 2),
                    "throughput_embeddings_per_second": round(throughput, 2),
                },
                notes=notes,
            )

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(documents),
            ),
            candidates=list(candidates.values()),
        )
