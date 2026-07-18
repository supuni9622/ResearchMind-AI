"""
Retrieval Report builder (AI Runtime Observability PRD §7 "Retrieval
Report"). Renders a `RetrievalMetricsSnapshot` as human-readable Markdown.
"""

from __future__ import annotations

from app.ai.observability.metrics.retrieval import RetrievalMetricsSnapshot


class RetrievalReportBuilder:
    @staticmethod
    def build(snapshot: RetrievalMetricsSnapshot) -> str:

        lines: list[str] = [
            "# Retrieval Report",
            "",
            f"- Retrieval ID: `{snapshot.retrieval_id}`",
            f"- Provider: {snapshot.provider.value if snapshot.provider else 'n/a'}",
            f"- Strategy: {snapshot.strategy.value if snapshot.strategy else 'n/a'}",
            "",
            "## Retrieval Latency",
            "",
            f"- Dense: {_fmt_ms(snapshot.dense_latency_ms)}",
            f"- Sparse: {_fmt_ms(snapshot.sparse_latency_ms)}",
            f"- Rerank: {_fmt_ms(snapshot.rerank_latency_ms)}",
            "",
            "## Reranking",
            "",
            f"- Provider: {snapshot.reranker_provider or 'n/a'}",
            "",
            "## Context",
            "",
            f"- Build Latency: {_fmt_ms(snapshot.context_build_latency_ms)}",
            f"- Compression Provider: {snapshot.compression_provider or 'n/a'}",
            f"- Guardrail Provider: {snapshot.guardrail_provider or 'n/a'}",
            "",
            "## Volume",
            "",
            f"- Retrieved Chunks: {snapshot.retrieved_chunks}",
            f"- Expanded Chunks: {_fmt_count(snapshot.expanded_chunks)}",
            f"- Compressed Chunks: {_fmt_count(snapshot.compressed_chunks)}",
            f"- Citations: {_fmt_count(snapshot.citations_count)}",
        ]

        return "\n".join(lines)


def _fmt_ms(value: float | None) -> str:
    return f"{value:.2f} ms" if value is not None else "n/a"


def _fmt_count(value: int | None) -> str:
    return str(value) if value is not None else "n/a"
