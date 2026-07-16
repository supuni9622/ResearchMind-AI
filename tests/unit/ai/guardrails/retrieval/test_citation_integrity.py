from __future__ import annotations

from uuid import uuid4

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.retrieval.citation_integrity import CitationIntegrityGuardrail

from tests.unit.ai.guardrails.factories import make_chunk, make_citation


async def test_check_alone_is_a_no_op() -> None:
    guardrail = CitationIntegrityGuardrail()

    assert await guardrail.check([make_chunk()]) == []


async def test_consistent_chunks_and_citations_produce_no_issues() -> None:
    guardrail = CitationIntegrityGuardrail()

    chunk = make_chunk(citation_id="S1")
    citation = make_citation(citation_id="S1", chunk_ids=[chunk.chunk_id])

    issues = await guardrail.check_citations(chunks=[chunk], citations=[citation])

    assert issues == []


async def test_citation_referencing_unknown_chunk_errors() -> None:
    guardrail = CitationIntegrityGuardrail()

    citation = make_citation(citation_id="S1", chunk_ids=[uuid4()])

    issues = await guardrail.check_citations(chunks=[], citations=[citation])

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.ERROR
    assert issues[0].category == GuardrailCategory.CITATION_INTEGRITY
    assert issues[0].code == "citation_references_unknown_chunk"


async def test_chunk_with_unresolved_citation_id_errors() -> None:
    guardrail = CitationIntegrityGuardrail()

    chunk = make_chunk(citation_id="S99")

    issues = await guardrail.check_citations(chunks=[chunk], citations=[])

    assert len(issues) == 1
    assert issues[0].code == "chunk_has_unresolved_citation"
