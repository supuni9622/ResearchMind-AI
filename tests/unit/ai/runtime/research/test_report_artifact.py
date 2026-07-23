from io import BytesIO
from uuid import uuid4

import pytest
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.report_artifact import ResearchFinalReportArtifactWriter
from app.ai.runtime.research.review import ResearchReview, ReviewDecision
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection
from pypdf import PdfReader

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


def _draft() -> ResearchDraft:
    return ResearchDraft(
        title="Reliable Research Runtime",
        abstract="A bounded report generated from validated evidence.",
        methodology="The system retrieves owner-scoped evidence and validates citations.",
        findings=[
            ResearchDraftSection(
                heading="Findings",
                content="Evidence-backed retrieval improves report traceability.",
                citation_ids=["citation-1"],
            )
        ],
        discussion="The result remains intentionally bounded by available evidence.",
        conclusion="A PDF makes the reviewed report portable.",
        citation_ids=["citation-1"],
        limitations=["This is a synthetic test report."],
    )


def _evidence() -> ResearchEvidenceBundle:
    return ResearchEvidenceBundle(
        citation_ids=["citation-1"],
        completed_task_count=1,
        failed_task_count=0,
    )


@pytest.mark.asyncio
async def test_final_report_writer_persists_downloadable_pdf_idempotently() -> None:
    storage = FakeDocumentStorage()
    writer = ResearchFinalReportArtifactWriter(storage)
    run_id = uuid4()
    review = ResearchReview(
        decision=ReviewDecision.PASS,
        citation_integrity_score=1,
        completeness_score=1,
    )

    first = await writer.write(
        research_run_id=run_id,
        draft=_draft(),
        review=review,
        evidence=_evidence(),
    )
    second = await writer.write(
        research_run_id=run_id,
        draft=_draft(),
        review=review,
        evidence=_evidence(),
    )

    assert first == second
    assert storage.uploads[first.pdf_ref].startswith(b"%PDF")
    reader = PdfReader(BytesIO(storage.uploads[first.pdf_ref]))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Abstract" in text
    assert "Methodology" in text
    assert "References" in text
    assert "citation-1" in text
    assert set(storage.uploads) == {first.report_ref, first.pdf_ref}
