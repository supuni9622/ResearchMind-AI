"""
Generation Report builder (AI Runtime Observability PRD §7 "Generation
Report"). Renders a `GenerationMetricsSnapshot` (already-computed --
never recomputed here) as human-readable Markdown.
"""

from __future__ import annotations

from app.ai.runtime.generation.observability.models import GenerationMetricsSnapshot


class GenerationReportBuilder:
    @staticmethod
    def build(snapshot: GenerationMetricsSnapshot) -> str:

        lines: list[str] = [
            "# Generation Report",
            "",
            f"- Generation ID: `{snapshot.generation_id}`",
            f"- Request ID: `{snapshot.request_id}`",
            f"- Runtime: {snapshot.runtime or 'n/a'}",
            f"- Provider / Model: {snapshot.provider.value} / {snapshot.model}",
            "",
            "## Latency",
            "",
            f"- Duration: {snapshot.latency_ms:.2f} ms",
            f"- Retries: {snapshot.retries}",
            f"- Regenerations: {snapshot.regeneration_count}",
            f"- Cache Hit: {snapshot.cache_hit}",
            "",
            "## Tokens",
            "",
            f"- Prompt Tokens: {snapshot.prompt_tokens}",
            f"- Completion Tokens: {snapshot.completion_tokens}",
            f"- Total Tokens: {snapshot.total_tokens}",
            "",
            "## Cost",
            "",
            f"- Estimated Cost (USD): {snapshot.estimated_cost_usd:.6f}",
        ]

        if snapshot.cumulative_session_cost_usd is not None:
            lines.append(
                f"- Cumulative Session Cost (USD): {snapshot.cumulative_session_cost_usd:.6f}"
            )

        lines.extend(
            [
                "",
                "## Validation",
                "",
                f"- Validation Score: {_fmt(snapshot.validation_score)}",
                f"- Hallucination Score: {_fmt(snapshot.hallucination_score)}",
                f"- Runtime Score: {_fmt(snapshot.runtime_score)}",
                "",
                "## Guardrails",
                "",
                f"- Risk Score: {_fmt(snapshot.guardrail_risk_score)}",
                f"- Blocked: {snapshot.guardrail_blocked}",
            ]
        )

        return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "n/a"
