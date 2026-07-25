"""Regression coverage for `ResearchService._runtime_evidence_metadata` --
the bridge that turns a completed Deep Research run's `ResearchEvidenceBundle`
into `Citation`/`ResearchSource` API metadata (`publish_runtime_report`).

Web evidence (web_search_tool_platform_prd.md) carries a URL in `document_id`
and a `"web:<uuid>"` string in `chunk_id`, neither of which is a valid `UUID`
literal -- unlike document evidence, whose ids are always real UUIDs. This
previously crashed with `ValueError: badly formed hexadecimal UUID string`
the first time a Deep Research run with `web_search_mode != disabled`
actually produced web evidence and reached report publication.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.research.service import ResearchService
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.retrieval.models import ResearchEvidenceReference


def _web_reference(citation_id: str = "W1-1") -> ResearchEvidenceReference:
    return ResearchEvidenceReference(
        document_id="https://ourworldindata.org/mental-health",
        chunk_id="web:078fb758-ffab-4d43-8421-ddf9c1463eeb",
        filename="Mental Health",
        citation_id=citation_id,
        score=0.4,
        excerpt="Mental health is an essential part of people's lives.",
        source_type="web",
    )


def _document_reference() -> ResearchEvidenceReference:
    return ResearchEvidenceReference(
        document_id="32b24391-4f53-43b8-92d5-e5f44f3cc37d",
        chunk_id="7c204780-d19b-4d5c-bdae-b755b9458a86",
        filename="report.pdf",
        citation_id="S1",
        score=0.8,
        excerpt="Grounded excerpt.",
        source_type="document",
    )


def test_web_evidence_does_not_raise_and_produces_a_stable_synthetic_uuid() -> None:
    bundle = ResearchEvidenceBundle(
        evidence=[_web_reference()], completed_task_count=1, failed_task_count=0
    )

    citations, sources = ResearchService._runtime_evidence_metadata(bundle)

    assert len(citations) == 1
    assert citations[0].citation_id == "W1-1"
    assert isinstance(citations[0].document_id, UUID)
    assert len(sources) == 1
    assert isinstance(sources[0].document_id, UUID)
    assert isinstance(sources[0].chunk_id, UUID)


def test_synthetic_uuid_is_deterministic_across_calls() -> None:
    bundle = ResearchEvidenceBundle(
        evidence=[_web_reference()], completed_task_count=1, failed_task_count=0
    )

    first_citations, _ = ResearchService._runtime_evidence_metadata(bundle)
    second_citations, _ = ResearchService._runtime_evidence_metadata(bundle)

    assert first_citations[0].document_id == second_citations[0].document_id


def test_document_and_web_evidence_coexist_in_the_same_bundle() -> None:
    bundle = ResearchEvidenceBundle(
        evidence=[_document_reference(), _web_reference()],
        completed_task_count=2,
        failed_task_count=0,
    )

    citations, sources = ResearchService._runtime_evidence_metadata(bundle)

    assert {c.citation_id for c in citations} == {"S1", "W1-1"}
    assert len(sources) == 2
    # The real document UUID is preserved unchanged (not re-derived).
    document_citation = next(c for c in citations if c.citation_id == "S1")
    assert document_citation.document_id == UUID("32b24391-4f53-43b8-92d5-e5f44f3cc37d")


def test_second_web_search_round_gets_distinct_citation_markers() -> None:
    bundle = ResearchEvidenceBundle(
        evidence=[_web_reference("W1-1"), _web_reference("W2-1")],
        completed_task_count=1,
        failed_task_count=0,
    )

    citations, _ = ResearchService._runtime_evidence_metadata(bundle)

    assert {c.citation_id for c in citations} == {"W1-1", "W2-1"}
