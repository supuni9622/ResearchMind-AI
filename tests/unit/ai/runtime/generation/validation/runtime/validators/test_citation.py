"""
Unit tests for RuntimeCitationValidator.

Covers:
- A structured citations list referencing only known citations has no issue
- A citations/evidence entry referencing an unknown citation is an ERROR
- Evidence citation_id references are checked the same way as citations
- No known citations in the prompt context means nothing to check
- No structured citation/evidence fields on the output means nothing to check
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.runtime.validators.citation import (
    RuntimeCitationValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import (
    make_citation,
    make_prompt_context,
    make_request,
    make_result,
)


async def test_known_citations_have_no_issue() -> None:
    validator = RuntimeCitationValidator()

    prompt_context = make_prompt_context(citations=[make_citation(citation_id="S1")])
    request = make_request(prompt_context=prompt_context)

    result = make_result(request=request, parsed_output={"citations": ["S1"]})

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_unknown_citation_is_an_error() -> None:
    validator = RuntimeCitationValidator()

    prompt_context = make_prompt_context(citations=[make_citation(citation_id="S1")])
    request = make_request(prompt_context=prompt_context)

    result = make_result(request=request, parsed_output={"citations": ["S1", "S99"]})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert "S99" in outcome.issues[0].message


async def test_unknown_evidence_citation_id_is_an_error() -> None:
    validator = RuntimeCitationValidator()

    prompt_context = make_prompt_context(citations=[make_citation(citation_id="S1")])
    request = make_request(prompt_context=prompt_context)

    result = make_result(
        request=request,
        parsed_output={"evidence": [{"content": "x", "citation_id": "S99"}]},
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert "S99" in outcome.issues[0].message


async def test_no_known_citations_means_nothing_to_check() -> None:
    validator = RuntimeCitationValidator()

    request = make_request(prompt_context=make_prompt_context(citations=[]))

    result = make_result(request=request, parsed_output={"citations": ["S99"]})

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_no_structured_citation_fields_means_nothing_to_check() -> None:
    validator = RuntimeCitationValidator()

    prompt_context = make_prompt_context(citations=[make_citation(citation_id="S1")])
    request = make_request(prompt_context=prompt_context)

    result = make_result(request=request, parsed_output={"summary": "no citations here"})

    outcome = await validator.validate(result)

    assert outcome.issues == []
