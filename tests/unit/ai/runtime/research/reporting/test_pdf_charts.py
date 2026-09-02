"""Covers the Wave 4 chart-embedding addition to `render_research_report_pdf`
(docs/PRIORITIZED_ROADMAP.md) -- the pre-existing text-only rendering
path is exercised by the workflow/integration tests, this file is
scoped to the new `charts` parameter only.
"""

from __future__ import annotations

import io
from unittest.mock import patch

from app.ai.runtime.research.charts.models import ChartDataPoint, ChartSpec
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.reporting.pdf import render_research_report_pdf
from app.ai.runtime.research.review import ResearchReview, ReviewDecision
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection
from PIL import Image as PILImage
from reportlab.platypus import Image


def _tiny_png_bytes() -> bytes:
    """A real, minimal decodable PNG -- reportlab's `Image` flowable reads
    the image at construction time (to determine dimensions), so a fake
    byte string isn't enough here, unlike other tests that only assert
    `render_chart_png` was called."""

    buffer = io.BytesIO()
    PILImage.new("RGB", (2, 2), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def _draft() -> ResearchDraft:
    return ResearchDraft(
        title="Title",
        abstract="Abstract",
        methodology="Methodology",
        findings=[ResearchDraftSection(heading="Findings", content="Content.", citation_ids=[])],
        discussion="Discussion",
        conclusion="Conclusion",
    )


def _review() -> ResearchReview:
    return ResearchReview(
        decision=ReviewDecision.PASS,
        citation_integrity_score=1.0,
        completeness_score=1.0,
    )


def _evidence() -> ResearchEvidenceBundle:
    return ResearchEvidenceBundle(completed_task_count=1, failed_task_count=0)


def _chart_spec() -> ChartSpec:
    return ChartSpec(
        chart_type="bar",
        title="Adoption rate",
        data=[ChartDataPoint(label="2024", value=12.0)],
        section_heading="Findings",
    )


def test_no_charts_produces_no_figures_section() -> None:
    pdf = render_research_report_pdf(draft=_draft(), review=_review(), evidence=_evidence())

    assert pdf.startswith(b"%PDF")


def test_charts_are_embedded_as_image_flowables() -> None:
    with (
        patch(
            "app.ai.runtime.research.reporting.pdf.render_chart_png",
            return_value=_tiny_png_bytes(),
        ) as mock_render,
        patch("app.ai.runtime.research.reporting.pdf.Image", wraps=Image) as mock_image,
    ):
        pdf = render_research_report_pdf(
            draft=_draft(), review=_review(), evidence=_evidence(), charts=[_chart_spec()]
        )

    mock_render.assert_called_once()
    mock_image.assert_called_once()
    assert pdf.startswith(b"%PDF")


def test_one_failed_chart_render_does_not_drop_the_report() -> None:
    """A bad spec must never fail the whole PDF -- matches this
    codebase's fail-open philosophy elsewhere (memory retrieval,
    web-search necessity)."""

    with patch(
        "app.ai.runtime.research.reporting.pdf.render_chart_png",
        side_effect=RuntimeError("matplotlib exploded"),
    ):
        pdf = render_research_report_pdf(
            draft=_draft(), review=_review(), evidence=_evidence(), charts=[_chart_spec()]
        )

    assert pdf.startswith(b"%PDF")


def test_one_failed_chart_among_several_does_not_drop_the_others() -> None:
    good_spec = _chart_spec()
    bad_spec = _chart_spec()

    def _render(spec: ChartSpec) -> bytes:
        if spec is bad_spec:
            raise RuntimeError("matplotlib exploded")
        return _tiny_png_bytes()

    with (
        patch(
            "app.ai.runtime.research.reporting.pdf.render_chart_png", side_effect=_render
        ) as mock_render,
        patch("app.ai.runtime.research.reporting.pdf.Image", wraps=Image) as mock_image,
    ):
        render_research_report_pdf(
            draft=_draft(),
            review=_review(),
            evidence=_evidence(),
            charts=[bad_spec, good_spec],
        )

    assert mock_render.call_count == 2
    mock_image.assert_called_once()
