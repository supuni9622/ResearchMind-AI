"""Render a `ChartSpec` (docs/PRIORITIZED_ROADMAP.md Wave 4: AI-generated
charts in Deep Research reports) into a deterministic PNG, purely from
the numbers already extracted by `ChartGenerationService` -- no LLM call
here, no image generation model. Matplotlib's non-interactive `Agg`
backend is used explicitly so this works headless in a server process
with no display, matching how the rest of this codebase's report
generation (`reporting/pdf.py`) has no browser/UI dependency either.
"""

from __future__ import annotations

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  (backend must be set first)

from app.ai.runtime.research.charts.models import ChartSpec  # noqa: E402


def render_chart_png(spec: ChartSpec) -> bytes:
    """Render `spec` to PNG bytes. Raises on failure -- callers (the PDF
    builder) are responsible for the per-chart fail-open behavior, so one
    bad spec never drops the rest of the report's figures."""

    labels = [point.label for point in spec.data]
    values = [point.value for point in spec.data]

    fig, ax = plt.subplots(figsize=(6, 4))
    try:
        if spec.chart_type == "bar":
            ax.bar(labels, values, color="#1D4ED8")
        elif spec.chart_type == "line":
            ax.plot(labels, values, marker="o", color="#1D4ED8")
        elif spec.chart_type == "pie":
            ax.pie(values, labels=labels, autopct="%1.0f%%")

        ax.set_title(spec.title)
        if spec.chart_type != "pie":
            if spec.x_label:
                ax.set_xlabel(spec.x_label)
            if spec.y_label:
                ax.set_ylabel(spec.y_label)
            ax.tick_params(axis="x", rotation=30)

        buffer = BytesIO()
        fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        return buffer.getvalue()
    finally:
        plt.close(fig)
