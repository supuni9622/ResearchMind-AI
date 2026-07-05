"""
Chunking benchmark.

Benchmarks every registered chunking provider using the same benchmark
dataset and produces a canonical BenchmarkReport.

The benchmark intentionally operates directly on canonical
ProcessedDocument models without requiring S3, workers, or queues.
"""

from __future__ import annotations

from pathlib import Path

from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.registry import ChunkingRegistry

from benchmarks.common.dataset_loader import DatasetLoader
from benchmarks.interfaces.benchmark import Benchmark
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkReport,
)


class ChunkingBenchmark(Benchmark):
    """
    Engineering benchmark for the Chunking Platform.
    """

    def __init__(
        self,
        *,
        registry: ChunkingRegistry,
        artifact_builder: ChunkArtifactBuilder,
        dataset_loader: DatasetLoader,
    ) -> None:
        self._registry = registry
        self._artifact_builder = artifact_builder
        self._dataset_loader = dataset_loader

    @property
    def name(self) -> str:
        return "Chunking"

    async def run(
        self,
        dataset_path: Path,
    ) -> BenchmarkReport:
        """
        Execute the chunking benchmark.

        Args:
            dataset_path:
                Root benchmark dataset directory.

        Returns:
            Canonical benchmark report.
        """

        documents = self._dataset_loader.load_documents(
            dataset_path,
        )

        candidates: dict[str, BenchmarkCandidate] = {}

        for provider in self._registry.providers.values():
            total_documents = 0
            total_chunks = 0
            total_characters = 0
            total_words = 0
            total_tokens = 0
            min_chunk_size: int | None = None
            max_chunk_size = 0

            for document in documents:
                chunks = await provider.chunk(document)

                artifact = self._artifact_builder.build(chunks)

                stats = artifact.statistics

                total_documents += 1
                total_chunks += stats.total_chunks
                total_characters += stats.total_characters
                total_words += stats.total_words
                total_tokens += stats.total_estimated_tokens

                if min_chunk_size is None or stats.average_chunk_size < min_chunk_size:
                    min_chunk_size = int(stats.average_chunk_size)

                max_chunk_size = max(
                    max_chunk_size,
                    int(stats.average_chunk_size),
                )

            average_chunk_size = total_characters / total_chunks if total_chunks else 0

            average_word_count = total_words / total_chunks if total_chunks else 0

            average_token_count = total_tokens / total_chunks if total_chunks else 0

            candidates[provider.strategy.value] = BenchmarkCandidate(
                name=provider.strategy.value,
                version=provider.version,
                metrics={
                    "documents": total_documents,
                    "total_chunks": total_chunks,
                    "average_chunk_size": round(
                        average_chunk_size,
                        2,
                    ),
                    "average_word_count": round(
                        average_word_count,
                        2,
                    ),
                    "average_token_count": round(
                        average_token_count,
                        2,
                    ),
                    "min_chunk_size": min_chunk_size or 0,
                    "max_chunk_size": max_chunk_size,
                },
            )

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(documents),
            ),
            candidates=list(candidates.values()),
        )
