"""
Engineering benchmark interface.

A benchmark evaluates one or more AI implementations using a shared
benchmark dataset and produces a canonical BenchmarkReport.

Concrete implementations include:

- ChunkingBenchmark
- EmbeddingBenchmark
- RetrievalBenchmark
- RerankingBenchmark
- PipelineBenchmark

Benchmarks are executed manually and are independent from production
infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from benchmarks.models.report import BenchmarkReport


class Benchmark(ABC):
    """
    Base interface for all engineering benchmarks.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Human-readable benchmark name.
        """
        raise NotImplementedError

    @abstractmethod
    async def run(
        self,
        dataset_path: Path,
    ) -> BenchmarkReport:
        """
        Execute the benchmark using the supplied benchmark dataset.

        Args:
        dataset_path:
            Root directory containing benchmark datasets.

        Returns:
        Canonical benchmark report.
        """
        raise NotImplementedError
