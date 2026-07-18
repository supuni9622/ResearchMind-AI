"""
System Report builder (AI Runtime Observability PRD §7 "System Report").
Renders a `StatisticsSnapshot` -- provider/cost/cache statistics -- as
human-readable Markdown.
"""

from __future__ import annotations

from app.ai.observability.statistics.models import RankingEntry, StatisticsSnapshot


class SystemReportBuilder:
    @staticmethod
    def build(statistics: StatisticsSnapshot) -> str:

        lines: list[str] = [
            "# System Report",
            "",
            f"- Window: {statistics.window.value if statistics.window else 'n/a'}",
            f"- Sample Count: {statistics.sample_count}",
        ]

        if statistics.sample_count == 0:
            return "\n".join(lines)

        lines.extend(
            [
                "",
                "## Percentiles",
                "",
            ]
        )

        if statistics.latency_percentiles is not None:
            p = statistics.latency_percentiles
            lines.extend(
                [
                    f"- p50: {p.p50:.2f} ms",
                    f"- p90: {p.p90:.2f} ms",
                    f"- p95: {p.p95:.2f} ms",
                    f"- p99: {p.p99:.2f} ms",
                ]
            )
        else:
            lines.append("- n/a")

        lines.extend(
            [
                "",
                "## Aggregations",
                "",
                f"- Average Latency: {_fmt(statistics.average_latency_ms, ' ms')}",
                f"- Average Cost: {_fmt(statistics.average_cost_usd, ' USD')}",
                f"- Average Tokens: {_fmt(statistics.average_tokens)}",
                f"- Average TTFT: {_fmt(statistics.average_ttft_ms, ' ms')}",
                f"- Average TPS: {_fmt(statistics.average_tps)}",
                f"- Error Rate: {_fmt_pct(statistics.error_rate)}",
                f"- Cache Hit Rate: {_fmt_pct(statistics.cache_hit_rate)}",
                f"- Hallucination Rate: {_fmt_pct(statistics.hallucination_rate)}",
                "",
                "## Provider Rankings",
                "",
                _ranking_table(statistics.provider_rankings),
                "",
                "## Model Rankings",
                "",
                _ranking_table(statistics.model_rankings),
                "",
                "## Cost Rankings",
                "",
                _ranking_table(statistics.cost_rankings),
                "",
                "## Latency Rankings",
                "",
                _ranking_table(statistics.latency_rankings),
            ]
        )

        return "\n".join(lines)


def _fmt(value: float | None, suffix: str = "") -> str:
    return f"{value:.2f}{suffix}" if value is not None else "n/a"


def _fmt_pct(value: float | None) -> str:
    return f"{value * 100:.1f}%" if value is not None else "n/a"


def _ranking_table(entries: list[RankingEntry]) -> str:
    if not entries:
        return "n/a"

    return "\n".join(
        f"{i + 1}. {entry.key} — {entry.value:.4f} (n={entry.sample_count})"
        for i, entry in enumerate(entries)
    )
