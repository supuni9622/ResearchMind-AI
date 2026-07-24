"""Render bounded Research Runtime drafts as readable, downloadable PDFs."""

from __future__ import annotations

from html import escape
from io import BytesIO
from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus.flowables import Flowable

from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.review import ResearchReview
from app.ai.runtime.research.synthesis.models import ResearchDraft

if TYPE_CHECKING:
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus.doctemplate import BaseDocTemplate


def render_research_report_pdf(
    *,
    draft: ResearchDraft,
    review: ResearchReview,
    evidence: ResearchEvidenceBundle,
) -> bytes:
    """Return a self-contained standard research-report PDF.

    Only the compact, validated report and evidence metadata are rendered. Raw
    provider output, full documents, and graph context deliberately stay out of
    the artifact.
    """

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=draft.title,
        author="ResearchMind AI",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ResearchMindTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    heading_style = ParagraphStyle(
        "ResearchMindHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#1D4ED8"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ResearchMindBody",
        parent=styles["BodyText"],
        leading=15,
        spaceAfter=8,
    )

    story: list[Flowable] = [Paragraph(_safe_text(draft.title), title_style)]
    _append_section(story, "Abstract", draft.abstract, heading_style, body_style)
    _append_section(story, "Methodology", draft.methodology, heading_style, body_style)
    for finding in draft.findings:
        _append_section(story, finding.heading, finding.content, heading_style, body_style)
        if finding.citation_ids:
            story.append(
                Paragraph(
                    _safe_text(f"Citations: {', '.join(finding.citation_ids)}"),
                    body_style,
                )
            )
    _append_section(story, "Discussion", draft.discussion, heading_style, body_style)
    _append_section(story, "Conclusion", draft.conclusion, heading_style, body_style)
    if draft.limitations or review.limitations:
        _append_section(
            story,
            "Limitations",
            "\n".join(f"- {item}" for item in [*draft.limitations, *review.limitations]),
            heading_style,
            body_style,
        )
    _append_references(story, draft, evidence, heading_style, body_style)
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            _safe_text(
                "ResearchMind quality review: "
                f"{review.decision.value} "
                f"(citation integrity {review.citation_integrity_score:.0%}, "
                f"completeness {review.completeness_score:.0%})."
            ),
            body_style,
        )
    )
    document.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return output.getvalue()


def _append_section(
    story: list[Flowable],
    heading: str,
    content: str,
    heading_style: ParagraphStyle,
    body_style: ParagraphStyle,
) -> None:
    story.append(Paragraph(_safe_text(heading), heading_style))
    story.append(Paragraph(_safe_text(content), body_style))


def _append_references(
    story: list[Flowable],
    draft: ResearchDraft,
    evidence: ResearchEvidenceBundle,
    heading_style: ParagraphStyle,
    body_style: ParagraphStyle,
) -> None:
    story.append(Paragraph("References", heading_style))
    evidence_by_citation = {item.citation_id: item for item in evidence.evidence}
    used = set(draft.citation_ids)
    for finding in draft.findings:
        used.update(finding.citation_ids)
    for citation_id in sorted(used):
        item = evidence_by_citation.get(citation_id)
        label = item.filename if item is not None else "Evidence reference unavailable"
        story.append(Paragraph(_safe_text(f"[{citation_id}] {label}"), body_style))


def _safe_text(value: str) -> str:
    return escape(value).replace("\n", "<br/>")


def _draw_footer(canvas: Canvas, document: BaseDocTemplate) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(0.75 * inch, 0.45 * inch, "ResearchMind AI - Research Runtime")
    canvas.drawRightString(7.75 * inch, 0.45 * inch, f"Page {document.page}")
    canvas.restoreState()
