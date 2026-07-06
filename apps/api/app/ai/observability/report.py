from __future__ import annotations

from app.ai.observability.models import PipelineRuntimeMetrics


class RuntimeReportBuilder:
    """Builds a human-readable runtime report."""

    @staticmethod
    def build(metrics: PipelineRuntimeMetrics) -> str:
        """Build a formatted runtime report."""

        lines: list[str] = [
            "Pipeline Runtime Metrics",
            "-" * 40,
            "",
            "Stages",
            "",
        ]

        for stage in metrics.stages:
            lines.append(
                f"{stage.stage:<20} "
                f"{stage.duration_ms:.2f} ms "
                f"(Peak Memory: {stage.peak_memory_mb:.2f} MB)"
            )

        lines.extend(
            [
                "",
                "-" * 40,
                "",
                "Artifacts",
                "",
            ]
        )

        if metrics.artifacts:
            for artifact in metrics.artifacts:
                lines.append(
                    f"{artifact.name:<20} {RuntimeReportBuilder._format_bytes(artifact.size_bytes)}"
                )
        else:
            lines.append("None")

        lines.extend(
            [
                "",
                "-" * 40,
                "",
                f"Peak Memory      : {metrics.peak_memory_mb:.2f} MB",
                f"Pipeline Duration: {metrics.total_duration_ms:.2f} ms",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Convert bytes into a human-readable string."""

        units = ["B", "KB", "MB", "GB", "TB"]

        value = float(size)

        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.2f} {unit}"
            value /= 1024

        return f"{value:.2f} TB"
