"""
Regression report generator.

Generates human-readable and machine-readable reports from a
RegressionResult (PRD §19 "Regression Report": metric changes,
threshold violations, pass/fail).
"""

from __future__ import annotations

import json

from benchmarks.regression.models import RegressionResult


class RegressionReportGenerator:
    """
    Generates reports from RegressionResult models.
    """

    def generate_markdown(
        self,
        result: RegressionResult,
    ) -> str:
        """
        Generate a Markdown regression report.
        """

        lines: list[str] = []

        lines.append(f"# {result.benchmark_name} — Regression Check")
        lines.append("")
        lines.append(f"- **Checked:** `{result.checked_at.isoformat()}`")
        lines.append(f"- **Status:** {'✅ PASSED' if result.passed else '❌ FAILED'}")
        lines.append(
            f"- **Commit:** `{result.previous_commit or 'unknown'}` -> "
            f"`{result.current_commit or 'unknown'}`"
        )
        lines.append(
            f"- **Dataset version:** `{result.previous_dataset_version}` -> "
            f"`{result.current_dataset_version}`"
        )
        lines.append("")

        if (
            result.regressions
            and result.previous_commit is not None
            and result.previous_commit == result.current_commit
        ):
            lines.append(
                "> ⚠️ No code changed between these two runs (same commit) -- "
                "these violations are likely run-to-run noise (e.g. live LLM "
                "sampling variance or provider latency jitter), not a real "
                "regression. Investigate before treating this as a defect."
            )
            lines.append("")

        if not result.regressions:
            lines.append("No regressions detected.")
            lines.append("")
            return "\n".join(lines)

        lines.append("## Threshold Violations")
        lines.append("")
        lines.append("| Candidate | Metric | Previous | Current | Threshold |")
        lines.append("|---|---|---:|---:|---:|")

        for issue in result.regressions:
            lines.append(
                f"| {issue.candidate} | {issue.metric} | {issue.previous_value:.4f} "
                f"| {issue.current_value:.4f} | {issue.threshold:.4f} |"
            )

        lines.append("")
        lines.append("## Details")
        lines.append("")

        for issue in result.regressions:
            lines.append(f"- **{issue.candidate} / {issue.metric}**: {issue.message}")

        lines.append("")

        return "\n".join(lines)

    def generate_json(
        self,
        result: RegressionResult,
        *,
        indent: int = 2,
    ) -> str:
        """
        Generate a JSON regression report.
        """

        return json.dumps(
            result.model_dump(mode="json"),
            indent=indent,
        )
