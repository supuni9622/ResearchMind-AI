"""
Ingestion Pipeline Benchmark.

Executes the complete ResearchMind ingestion pipeline against the
benchmark dataset and produces a comprehensive engineering report:

    Chunking -> Embedding (Voyage AI) -> Indexing (Qdrant) -> Persist Artifacts

Every document is processed independently through real, unmocked
production services (see ``benchmarks/pipeline/services.py``), and
every stage is measured with the same ``RuntimeMetricsCollector`` used
in production.

This benchmark intentionally does not implement
``benchmarks.interfaces.benchmark.Benchmark``. That interface returns
the generic ``BenchmarkReport``, built to compare several named
implementations of one platform on one shared metric table. The
Pipeline Benchmark instead runs a single, complete, real pipeline
across every document and reports much richer per-document, aggregate,
throughput, storage, and memory metrics -- a different report shape,
defined in ``benchmarks/pipeline/models.py``. It therefore has its own
CLI entry point below rather than going through ``benchmarks/runner.py``.

If any document fails, the benchmark aborts immediately -- it does not
skip failed documents and continue.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import subprocess
import time
from pathlib import Path

from benchmarks.pipeline.dataset import load_pipeline_dataset
from benchmarks.pipeline.models import (
    DocumentPipelineResult,
    MemorySummary,
    Observations,
    PipelineBenchmarkReport,
    ProductionReadiness,
    StatSummary,
    StorageSummary,
    SuccessReport,
    ThroughputSummary,
)
from benchmarks.pipeline.pipeline_runner import (
    CHUNKING_STRATEGY,
    EMBEDDING_PROVIDER,
    run_document_pipeline,
)
from benchmarks.pipeline.report_generator import PipelineReportGenerator
from benchmarks.pipeline.services import create_pipeline_services
from benchmarks.pipeline.stats import summarize

OWNER_ID = "benchmark-ingestion-pipeline"


class PipelineBenchmark:
    """
    End-to-end ingestion pipeline benchmark.
    """

    @property
    def name(self) -> str:
        return "Ingestion Pipeline"

    async def run(
        self,
        dataset_path: Path,
    ) -> PipelineBenchmarkReport:
        """
        Execute the complete ingestion pipeline for every document in the
        benchmark dataset and return the aggregated benchmark report.
        """

        entries = load_pipeline_dataset(dataset_path)

        if not entries:
            raise RuntimeError(f"Benchmark dataset is empty: {dataset_path}")

        services = create_pipeline_services()

        results: list[DocumentPipelineResult] = []
        wall_clock = time.perf_counter()

        for index, entry in enumerate(entries, start=1):
            print(f"[{index}/{len(entries)}] Processing {entry.document.filename} ...")

            try:
                result = await run_document_pipeline(
                    document=entry.document,
                    source_size_bytes=entry.source_size_bytes,
                    services=services,
                    owner_id=OWNER_ID,
                    on_progress=print,
                )
            except Exception as exc:
                print(f"FAILED: {entry.document.filename}: {exc}")
                raise

            print(
                f"  done in {result.total_duration_ms / 1000:.2f}s "
                f"(peak memory {result.peak_memory_mb:.1f} MB)"
            )
            results.append(result)

        wall_clock_seconds = time.perf_counter() - wall_clock

        return self._build_report(
            dataset_path=dataset_path,
            results=results,
            wall_clock_seconds=wall_clock_seconds,
        )

    def _build_report(
        self,
        *,
        dataset_path: Path,
        results: list[DocumentPipelineResult],
        wall_clock_seconds: float,
    ) -> PipelineBenchmarkReport:
        pipeline_durations = [r.total_duration_ms for r in results]
        processing_durations = [0.0 for _ in results]
        chunking_durations = [r.chunking.duration_ms for r in results]
        embedding_durations = [r.embedding.duration_ms for r in results]
        indexing_durations = [r.indexing.duration_ms for r in results]
        chunk_counts = [float(r.chunking.chunk_count) for r in results]
        embedding_counts = [float(r.embedding.embedding_count) for r in results]
        vector_counts = [float(r.indexing.vector_count) for r in results]
        artifact_totals = [float(r.artifacts.total_bytes) for r in results]
        peak_memories = [r.peak_memory_mb for r in results]

        pipeline_timing = {
            "total_pipeline_duration_ms": summarize(pipeline_durations),
            "processing_duration_ms": summarize(processing_durations),
            "chunking_duration_ms": summarize(chunking_durations),
            "embedding_duration_ms": summarize(embedding_durations),
            "indexing_duration_ms": summarize(indexing_durations),
        }

        aggregate_statistics = {
            "chunk_count": summarize(chunk_counts),
            "embedding_count": summarize(embedding_counts),
            "artifact_size_bytes": summarize(artifact_totals),
        }

        total_bytes_generated = sum(r.artifacts.total_bytes for r in results)
        total_chunks = sum(r.chunking.chunk_count for r in results)
        total_embeddings = sum(r.embedding.embedding_count for r in results)

        storage = StorageSummary(
            average_bytes_per_document=total_bytes_generated / len(results),
            average_bytes_per_chunk=(
                sum(r.artifacts.chunks_json_bytes for r in results) / total_chunks
                if total_chunks
                else 0.0
            ),
            average_bytes_per_embedding=(
                sum(r.artifacts.embeddings_json_bytes for r in results) / total_embeddings
                if total_embeddings
                else 0.0
            ),
            total_bytes_generated=total_bytes_generated,
            average_processed_document_json_bytes=(
                sum(r.artifacts.processed_document_json_bytes for r in results) / len(results)
            ),
            average_chunks_json_bytes=(
                sum(r.artifacts.chunks_json_bytes for r in results) / len(results)
            ),
            average_embeddings_json_bytes=(
                sum(r.artifacts.embeddings_json_bytes for r in results) / len(results)
            ),
            average_indexing_json_bytes=(
                sum(r.artifacts.indexing_json_bytes for r in results) / len(results)
            ),
        )

        throughput = ThroughputSummary(
            documents_per_minute=(len(results) / wall_clock_seconds) * 60,
            chunks_per_second=sum(chunk_counts) / wall_clock_seconds,
            embeddings_per_second=sum(embedding_counts) / wall_clock_seconds,
            vectors_per_second=sum(vector_counts) / wall_clock_seconds,
        )

        memory = MemorySummary(
            average_peak_memory_mb=sum(peak_memories) / len(peak_memories),
            minimum_peak_memory_mb=min(peak_memories),
            maximum_peak_memory_mb=max(peak_memories),
        )

        success = SuccessReport(
            documents_processed=len(results),
            successful=len(results),
            failed=0,
            success_rate=100.0,
        )

        observations = self._build_observations(
            results=results,
            pipeline_timing=pipeline_timing,
            aggregate_statistics=aggregate_statistics,
        )

        production_readiness = self._build_production_readiness(
            success=success,
            pipeline_timing=pipeline_timing,
            observations=observations,
            storage=storage,
        )

        return PipelineBenchmarkReport(
            commit=self._resolve_git_commit(),
            environment=self._build_environment(results),
            dataset_name=dataset_path.name,
            dataset_directory=str(dataset_path),
            documents=results,
            pipeline_timing=pipeline_timing,
            aggregate_statistics=aggregate_statistics,
            throughput=throughput,
            storage=storage,
            memory=memory,
            success=success,
            observations=observations,
            production_readiness=production_readiness,
        )

    @staticmethod
    def _build_observations(
        *,
        results: list[DocumentPipelineResult],
        pipeline_timing: dict[str, StatSummary],
        aggregate_statistics: dict[str, StatSummary],
    ) -> Observations:
        slowest = max(results, key=lambda r: r.total_duration_ms)
        fastest = min(results, key=lambda r: r.total_duration_ms)

        artifact_entries: list[tuple[str, int]] = []
        for result in results:
            artifact_entries.append(
                (
                    f"{result.document.filename} / processed_document.json",
                    result.artifacts.processed_document_json_bytes,
                )
            )
            artifact_entries.append(
                (f"{result.document.filename} / chunks.json", result.artifacts.chunks_json_bytes)
            )
            artifact_entries.append(
                (
                    f"{result.document.filename} / embeddings.json",
                    result.artifacts.embeddings_json_bytes,
                )
            )
            artifact_entries.append(
                (
                    f"{result.document.filename} / indexing.json",
                    result.artifacts.indexing_json_bytes,
                )
            )

        largest = max(artifact_entries, key=lambda entry: entry[1])
        smallest = min(artifact_entries, key=lambda entry: entry[1])

        return Observations(
            slowest_document=slowest.document.filename,
            slowest_document_duration_ms=slowest.total_duration_ms,
            fastest_document=fastest.document.filename,
            fastest_document_duration_ms=fastest.total_duration_ms,
            largest_artifact=largest[0],
            largest_artifact_bytes=largest[1],
            smallest_artifact=smallest[0],
            smallest_artifact_bytes=smallest[1],
            average_pipeline_time_ms=pipeline_timing["total_pipeline_duration_ms"].average,
            average_vectors_generated=(
                sum(r.indexing.vector_count for r in results) / len(results)
            ),
            average_chunks_generated=aggregate_statistics["chunk_count"].average,
        )

    @staticmethod
    def _build_production_readiness(
        *,
        success: SuccessReport,
        pipeline_timing: dict[str, StatSummary],
        observations: Observations,
        storage: StorageSummary,
    ) -> ProductionReadiness:
        stage_averages = {
            "Chunking": pipeline_timing["chunking_duration_ms"].average,
            "Embedding": pipeline_timing["embedding_duration_ms"].average,
            "Indexing": pipeline_timing["indexing_duration_ms"].average,
        }
        bottleneck_stage = max(stage_averages, key=lambda stage: stage_averages[stage])

        checks = [
            "Complete ingestion pipeline functional",
            f"{success.successful}/{success.documents_processed} documents successfully processed",
            f"{success.success_rate:.0f}% embedding success",
            f"{success.success_rate:.0f}% indexing success",
            "All artifacts generated",
            f"Average pipeline time: {observations.average_pipeline_time_ms / 1000:.2f} s",
            f"Average vectors indexed: {observations.average_vectors_generated:.0f}",
            (
                "No failures observed"
                if success.failed == 0
                else f"{success.failed} failures observed"
            ),
        ]

        recommendations = [
            f"Optimize {bottleneck_stage.lower()} latency (largest contributor)",
            (
                "Artifact storage size is acceptable"
                if storage.average_bytes_per_document < 5_000_000
                else "Artifact storage per document is large; consider compression."
            ),
            (
                "Ready to proceed to Retrieval Platform"
                if success.failed == 0
                else "Investigate failures before proceeding to the Retrieval Platform."
            ),
        ]

        return ProductionReadiness(
            checks=checks,
            recommendations=recommendations,
        )

    @staticmethod
    def _build_environment(results: list[DocumentPipelineResult]) -> dict[str, str]:
        environment = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "chunking_strategy": CHUNKING_STRATEGY.value,
            "embedding_provider": EMBEDDING_PROVIDER.value,
            "vector_store_provider": "qdrant",
            "owner_id": OWNER_ID,
        }

        if results:
            environment["embedding_model"] = results[0].embedding.model
            environment["qdrant_collection"] = results[0].indexing.collection_name

        return environment

    @staticmethod
    def _resolve_git_commit() -> str | None:
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        commit = completed.stdout.strip()
        return commit or None


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the ResearchMind ingestion pipeline benchmark.",
    )

    parser.add_argument(
        "--dataset",
        default=Path("benchmarks/datasets/research-papers"),
        type=Path,
        help="Benchmark dataset directory.",
    )

    parser.add_argument(
        "--output",
        default=Path("benchmarks/reports"),
        type=Path,
        help="Output directory for the report files.",
    )

    args = parser.parse_args()

    benchmark = PipelineBenchmark()
    report = await benchmark.run(args.dataset)

    args.output.mkdir(parents=True, exist_ok=True)

    generator = PipelineReportGenerator()

    markdown_path = args.output / "ingestion-benchmark-report.md"
    json_path = args.output / "ingestion-benchmark.json"

    markdown_path.write_text(
        generator.generate_markdown(report),
        encoding="utf-8",
    )

    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    print()
    print(
        f"Benchmark completed: "
        f"{report.success.successful}/{report.success.documents_processed} documents"
    )
    print(f"Markdown report: {markdown_path}")
    print(f"JSON report:     {json_path}")


if __name__ == "__main__":
    asyncio.run(_main())
