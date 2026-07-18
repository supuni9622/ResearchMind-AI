"""
Benchmark report generator.

Generates human-readable reports from canonical BenchmarkReport models.

The generator is intentionally benchmark-agnostic and can render reports
for any engineering benchmark within ResearchMind, including:

- Chunking
- Embeddings
- Retrieval
- Reranking
- End-to-End Pipeline

Additional output formats may be added in the future.
"""

from __future__ import annotations

import json

from benchmarks.models.report import BenchmarkReport


class BenchmarkReportGenerator:
    """
    Generates reports from BenchmarkReport models.
    """

    def generate_markdown(
        self,
        report: BenchmarkReport,
    ) -> str:
        """
        Generate a Markdown report.

        Args:
            report:
                Benchmark report.

        Returns:
            Markdown representation.
        """

        lines: list[str] = []

        lines.append(f"# {report.benchmark_name}")
        lines.append("")

        lines.append("## Dataset")
        lines.append("")
        lines.append(f"- **Name:** {report.dataset.name}")
        lines.append(f"- **Documents:** {report.dataset.document_count}")
        lines.append(f"- **Generated:** `{report.generated_at.isoformat()}`")
        lines.append("")

        lines.extend(self._generate_metadata_section(report))

        lines.append("---")
        lines.append("")

        if report.candidates:
            lines.extend(self._generate_summary_table(report))

            lines.append("")
            lines.append("---")
            lines.append("")

            for candidate in report.candidates:
                lines.extend(
                    self._generate_candidate_section(
                        candidate,
                    )
                )

        return "\n".join(lines)

    def generate_json(
        self,
        report: BenchmarkReport,
        *,
        indent: int = 2,
    ) -> str:
        """
        Generate a JSON report.

        Args:
            report:
                Benchmark report.

            indent:
                JSON indentation.

        Returns:
            JSON representation.
        """

        return json.dumps(
            report.model_dump(
                mode="json",
            ),
            indent=indent,
        )

    def _generate_metadata_section(
        self,
        report: BenchmarkReport,
    ) -> list[str]:
        """
        Generate the run-provenance section (commit, branch, dataset
        and model versions) so a regression can be traced back to what
        actually changed between two runs.
        """

        metadata = report.metadata

        lines: list[str] = []

        lines.append("## Provenance")
        lines.append("")
        lines.append(f"- **Git commit:** `{metadata.git_commit or 'unknown'}`")
        lines.append(f"- **Branch:** `{metadata.branch or 'unknown'}`")
        lines.append(f"- **Dataset version:** `{metadata.dataset_version}`")
        lines.append(f"- **Benchmark version:** `{metadata.benchmark_version}`")

        if metadata.model_versions:
            lines.append("- **Model versions:**")

            for candidate_name, model in sorted(metadata.model_versions.items()):
                lines.append(f"  - `{candidate_name}`: `{model}`")

        lines.append("")

        return lines

    def _generate_summary_table(
        self,
        report: BenchmarkReport,
    ) -> list[str]:
        """
        Generate the benchmark comparison table.
        """

        metrics: list[str] = sorted(
            {metric for candidate in report.candidates for metric in candidate.metrics}
        )

        lines: list[str] = []

        header = "| Metric |"
        separator = "|---|"

        for candidate in report.candidates:
            header += f" {candidate.name} |"
            separator += "---:|"

        lines.append("## Comparison")
        lines.append("")
        lines.append(header)
        lines.append(separator)

        for metric in metrics:
            row = f"| {metric.replace('_', ' ').title()} |"

            for candidate in report.candidates:
                value = candidate.metrics.get(metric, "-")
                row += f" {value} |"

            lines.append(row)

        return lines

    def _generate_candidate_section(
        self,
        candidate,
    ) -> list[str]:
        """
        Generate a detailed section for a benchmark candidate.
        """

        lines: list[str] = []

        lines.append(f"## {candidate.name}")
        lines.append("")

        if candidate.version:
            lines.append(f"Version: `{candidate.version}`")
            lines.append("")

        lines.append("| Metric | Value |")
        lines.append("|---|---:|")

        for metric, value in candidate.metrics.items():
            lines.append(f"| {metric.replace('_', ' ').title()} | {value} |")

        if candidate.notes:
            lines.append("")
            lines.append("### Notes")
            lines.append("")

            for key, value in candidate.notes.items():
                lines.append(f"- **{key}**: {value}")

        lines.append("")

        return lines
