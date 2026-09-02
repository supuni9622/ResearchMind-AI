from __future__ import annotations

import io

import pytest
from app.ai.runtime.research.charts.models import ChartDataPoint, ChartSpec
from app.ai.runtime.research.reporting.charts import render_chart_png
from PIL import Image


def _spec(chart_type: str) -> ChartSpec:
    return ChartSpec(
        chart_type=chart_type,
        title="Adoption rate by year",
        x_label="Year",
        y_label="Percent",
        data=[
            ChartDataPoint(label="2023", value=10.0),
            ChartDataPoint(label="2024", value=25.0),
            ChartDataPoint(label="2025", value=40.0),
        ],
    )


@pytest.mark.parametrize("chart_type", ["bar", "line", "pie"])
def test_render_chart_png_produces_a_valid_png(chart_type: str) -> None:
    png_bytes = render_chart_png(_spec(chart_type))

    assert png_bytes.startswith(b"\x89PNG")

    with Image.open(io.BytesIO(png_bytes)) as image:
        image.verify()
