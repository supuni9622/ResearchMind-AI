"""
Ingestion Pipeline Benchmark report generator.

Renders the canonical ``PipelineBenchmarkReport`` model into the
Markdown report layout used for engineering review.
"""

from __future__ import annotations

from benchmarks.pipeline.models import PipelineBenchmarkReport, StatSummary


class PipelineReportGenerator:
    """
    Generates the Markdown ingestion benchmark report.
    """

    def generate_markdown(
        self,
        report: PipelineBenchmarkReport,
    ) -> str:
        lines: list[str] = []

        lines.extend(self._header(report))
        lines.extend(self._environment_section(report))
        lines.extend(self._dataset_section(report))
        lines.extend(self._individual_results_section(report))
        lines.extend(self._aggregate_statistics_section(report))
        lines.extend(self._pipeline_timing_section(report))
        lines.extend(self._storage_section(report))
        lines.extend(self._throughput_section(report))
        lines.extend(self._memory_section(report))
        lines.extend(self._success_section(report))
        lines.extend(self._observations_section(report))
        lines.extend(self._production_readiness_section(report))

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _header(self, report: PipelineBenchmarkReport) -> list[str]:
        return [
            "# ResearchMind Ingestion Benchmark",
            "",
            f"**Date:** {report.generated_at.isoformat()}",
            f"**Commit:** `{report.commit}`" if report.commit else "**Commit:** N/A",
            "",
        ]

    def _environment_section(self, report: PipelineBenchmarkReport) -> list[str]:
        lines = ["## Environment", "", "| Key | Value |", "|---|---|"]

        for key, value in report.environment.items():
            lines.append(f"| {key.replace('_', ' ').title()} | {value} |")

        lines.append("")
        return lines

    def _dataset_section(self, report: PipelineBenchmarkReport) -> list[str]:
        documents = report.documents
        total_pages = sum(d.document.page_count for d in documents)
        total_characters = sum(d.document.character_count for d in documents)
        total_words = sum(d.document.word_count for d in documents)

        lines = [
            "## Dataset",
            "",
            f"- **Name:** {report.dataset_name}",
            f"- **Directory:** `{report.dataset_directory}`",
            f"- **Documents:** {len(documents)}",
            (
                "- **Note:** documents were loaded from pre-processed "
                "`processed_document.json` artifacts. Upload and Processing "
                "(PDF parsing) were not re-executed; 'File Size' reflects the "
                "size of that source JSON, not the original PDF."
            ),
            "",
            "### Dataset Summary",
            "",
            "| Metric | Total | Average per Document |",
            "|---|---:|---:|",
            f"| Pages | {total_pages} | {total_pages / len(documents):.1f} |",
            f"| Characters | {total_characters:,} | {total_characters / len(documents):,.0f} |",
            f"| Words | {total_words:,} | {total_words / len(documents):,.0f} |",
            "",
        ]

        return lines

    def _individual_results_section(self, report: PipelineBenchmarkReport) -> list[str]:
        lines = [
            "## Individual Document Results",
            "",
            "| Document | Pages | Chars | Words | Chunks | Avg Chunk | Largest | Smallest | "
            "Chunking (ms) | Embeddings | Dims | Embedding (ms) | Dense Vectors | "
            "Sparse Vectors | Indexing (ms) | Collection | Total (ms) | Peak Mem (MB) | "
            "Artifact Size |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
            "---:|---:|---:|",
        ]

        for result in report.documents:
            lines.append(
                f"| {result.document.filename} "
                f"| {result.document.page_count} "
                f"| {result.document.character_count:,} "
                f"| {result.document.word_count:,} "
                f"| {result.chunking.chunk_count} "
                f"| {result.chunking.average_chunk_size:.0f} "
                f"| {result.chunking.largest_chunk} "
                f"| {result.chunking.smallest_chunk} "
                f"| {result.chunking.duration_ms:.1f} "
                f"| {result.embedding.embedding_count} "
                f"| {result.embedding.dimensions} "
                f"| {result.embedding.duration_ms:.1f} "
                f"| {result.indexing.vector_count} "
                f"| {result.indexing.sparse_vector_count} "
                f"| {result.indexing.duration_ms:.1f} "
                f"| {result.indexing.collection_name} "
                f"| {result.total_duration_ms:.1f} "
                f"| {result.peak_memory_mb:.1f} "
                f"| {_format_bytes(result.artifacts.total_bytes)} |"
            )

        lines.append("")
        return lines

    def _aggregate_statistics_section(self, report: PipelineBenchmarkReport) -> list[str]:
        lines = [
            "## Aggregate Statistics",
            "",
            "| Metric | Average | Minimum | Maximum | Median | P95 |",
            "|---|---:|---:|---:|---:|---:|",
        ]

        labels = {
            "chunk_count": "Chunk Count",
            "embedding_count": "Embedding Count",
            "sparse_vector_count": "Sparse Vector Count",
            "artifact_size_bytes": "Artifact Size (bytes)",
        }

        for key, label in labels.items():
            lines.append(self._stat_row(label, report.aggregate_statistics[key]))

        lines.append("")
        return lines

    def _pipeline_timing_section(self, report: PipelineBenchmarkReport) -> list[str]:
        lines = [
            "## Pipeline Timing",
            "",
            "| Stage | Average (ms) | Minimum | Maximum | Median | P95 |",
            "|---|---:|---:|---:|---:|---:|",
        ]

        labels = {
            "total_pipeline_duration_ms": "Total Pipeline",
            "processing_duration_ms": "Processing (skipped)",
            "chunking_duration_ms": "Chunking",
            "embedding_duration_ms": "Embedding",
            "indexing_duration_ms": "Indexing",
        }

        for key, label in labels.items():
            lines.append(self._stat_row(label, report.pipeline_timing[key]))

        lines.append("")
        return lines

    def _storage_section(self, report: PipelineBenchmarkReport) -> list[str]:
        storage = report.storage
        per_doc = _format_bytes(storage.average_bytes_per_document)
        per_chunk = _format_bytes(storage.average_bytes_per_chunk)
        per_embedding = _format_bytes(storage.average_bytes_per_embedding)
        total = _format_bytes(storage.total_bytes_generated)
        avg_processed_document = _format_bytes(storage.average_processed_document_json_bytes)
        avg_chunks = _format_bytes(storage.average_chunks_json_bytes)
        avg_embeddings = _format_bytes(storage.average_embeddings_json_bytes)
        avg_indexing = _format_bytes(storage.average_indexing_json_bytes)

        return [
            "## Storage Report",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Average storage per document | {per_doc} |",
            f"| Average storage per chunk | {per_chunk} |",
            f"| Average storage per embedding | {per_embedding} |",
            f"| Total storage generated | {total} |",
            f"| Avg processed_document.json | {avg_processed_document} |",
            f"| Avg chunks.json | {avg_chunks} |",
            f"| Avg embeddings.json | {avg_embeddings} |",
            f"| Avg indexing.json | {avg_indexing} |",
            "",
        ]

    def _throughput_section(self, report: PipelineBenchmarkReport) -> list[str]:
        throughput = report.throughput
        return [
            "## Throughput",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Documents / minute | {throughput.documents_per_minute:.2f} |",
            f"| Chunks / second | {throughput.chunks_per_second:.2f} |",
            f"| Embeddings / second | {throughput.embeddings_per_second:.2f} |",
            f"| Vectors / second | {throughput.vectors_per_second:.2f} |",
            "",
        ]

    def _memory_section(self, report: PipelineBenchmarkReport) -> list[str]:
        memory = report.memory
        return [
            "## Memory Usage",
            "",
            "| Metric | Value (MB) |",
            "|---|---:|",
            f"| Average peak memory | {memory.average_peak_memory_mb:.1f} |",
            f"| Minimum peak memory | {memory.minimum_peak_memory_mb:.1f} |",
            f"| Maximum peak memory | {memory.maximum_peak_memory_mb:.1f} |",
            "",
        ]

    def _success_section(self, report: PipelineBenchmarkReport) -> list[str]:
        success = report.success
        return [
            "## Success Report",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Documents processed | {success.documents_processed} |",
            f"| Successful | {success.successful} |",
            f"| Failed | {success.failed} |",
            f"| Success Rate | {success.success_rate:.0f}% |",
            "",
        ]

    def _observations_section(self, report: PipelineBenchmarkReport) -> list[str]:
        observations = report.observations
        return [
            "## Observations",
            "",
            (
                f"- **Slowest document:** {observations.slowest_document} "
                f"({observations.slowest_document_duration_ms / 1000:.2f}s)"
            ),
            (
                f"- **Fastest document:** {observations.fastest_document} "
                f"({observations.fastest_document_duration_ms / 1000:.2f}s)"
            ),
            (
                f"- **Largest artifact:** {observations.largest_artifact} "
                f"({_format_bytes(observations.largest_artifact_bytes)})"
            ),
            (
                f"- **Smallest artifact:** {observations.smallest_artifact} "
                f"({_format_bytes(observations.smallest_artifact_bytes)})"
            ),
            f"- **Average pipeline time:** {observations.average_pipeline_time_ms / 1000:.2f}s",
            (
                f"- **Average dense vectors generated:** "
                f"{observations.average_vectors_generated:.0f}"
            ),
            (
                f"- **Average sparse vectors generated:** "
                f"{observations.average_sparse_vectors_generated:.0f}"
            ),
            f"- **Average chunks generated:** {observations.average_chunks_generated:.0f}",
            "",
        ]

    def _production_readiness_section(self, report: PipelineBenchmarkReport) -> list[str]:
        readiness = report.production_readiness

        lines = ["## Production Readiness", ""]
        lines.extend(f"✔ {check}" for check in readiness.checks)
        lines.append("")
        lines.append("### Recommendations")
        lines.append("")
        lines.extend(f"- {recommendation}" for recommendation in readiness.recommendations)
        lines.append("")

        return lines

    @staticmethod
    def _stat_row(label: str, summary: StatSummary) -> str:
        return (
            f"| {label} | {summary.average:.1f} | {summary.minimum:.1f} | "
            f"{summary.maximum:.1f} | {summary.median:.1f} | {summary.p95:.1f} |"
        )


def _format_bytes(size: float) -> str:
    """
    Convert a byte count into a human-readable string.
    """

    value = float(size)

    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{value:.2f} TB"
