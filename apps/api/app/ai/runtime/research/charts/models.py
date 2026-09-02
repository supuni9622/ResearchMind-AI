"""Research-Runtime-specific chart-generation decision/spec contracts.

Deep Research (Wave 4, docs/PRIORITIZED_ROADMAP.md) -- the model produces
or extracts structured chart data, a deterministic charting library
renders it. Never image *generation*: a chart must be data-accurate, not
merely plausible-looking, so no field here carries raw pixels or an
image-generation prompt.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ChartType = Literal["bar", "line", "pie"]


class ChartDataPoint(BaseModel):
    """One labeled numeric value -- an x/y pair for bar/line, a slice for pie."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=100)
    value: float


class ChartSpec(BaseModel):
    """A single chart's data and rendering intent.

    `data` is capped at 12 points -- a research-report figure, not a raw
    dataset dump. `section_heading`/`citation_ids` are deliberately
    optional but present: they let the rendered figure carry a caption
    back to the finding it illustrates and the evidence it's grounded in,
    for the same auditability reason citations are tracked everywhere
    else in this codebase.
    """

    model_config = ConfigDict(extra="forbid")

    chart_type: ChartType
    title: str = Field(min_length=1, max_length=150)
    x_label: str | None = Field(default=None, max_length=100)
    y_label: str | None = Field(default=None, max_length=100)
    data: list[ChartDataPoint] = Field(min_length=1, max_length=12)
    section_heading: str | None = Field(default=None, max_length=200)
    citation_ids: list[str] = Field(default_factory=list)


class ChartGenerationDecision(BaseModel):
    """Structured output of the cheap chart-necessity-and-extraction LLM
    call. One combined call, not a separate decide-then-extract pair
    (unlike web search): there is no external tool call to invoke after
    deciding, so a second round-trip would only add latency/cost for
    nothing -- see `necessity.py`."""

    model_config = ConfigDict(extra="forbid")

    needs_charts: bool
    charts: list[ChartSpec] = Field(default_factory=list, max_length=3)
    reason: str = Field(min_length=1, max_length=500)
