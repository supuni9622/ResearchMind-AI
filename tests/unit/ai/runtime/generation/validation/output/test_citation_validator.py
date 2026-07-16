"""
Unit tests for CitationValidator.

Covers:
- No known citations at all -> no-op (nothing to check against)
- All cited markers known -> valid
- Unknown citation marker -> ERROR listing the unknown id(s)
- Citation known only via a chunk's citation_id (no top-level Citation) -> counts as known
- Multiple markers in one bracket ("[S1, S2]") -> both parsed
- A bracketed token that isn't a plausible citation id (e.g. JSON-like) is ignored
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.output.citation_validator import CitationValidator

from tests.unit.ai.runtime.generation.validation.factories import (
    make_chunk,
    make_citation,
    make_prompt_context,
    make_request,
    make_result,
)

validator = CitationValidator()


async def test_validate_returns_empty_outcome_when_no_known_citations() -> None:
    result = make_result(
        request=make_request(prompt_context=make_prompt_context(chunks=[], citations=[])),
        content="The sky is blue [S1].",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_validate_passes_when_all_cited_markers_are_known() -> None:
    context = make_prompt_context(citations=[make_citation(citation_id="S1")])

    result = make_result(
        request=make_request(prompt_context=context),
        content="The sky is blue [S1].",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_validate_errors_on_unknown_citation_marker() -> None:
    context = make_prompt_context(citations=[make_citation(citation_id="S1")])

    result = make_result(
        request=make_request(prompt_context=context),
        content="The sky is blue [S1]. Grass is green [S2].",
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert outcome.issues[0].details["unknown_citations"] == ["S2"]


async def test_validate_accepts_citation_known_only_via_chunk() -> None:
    context = make_prompt_context(
        chunks=[make_chunk(citation_id="S1")],
        citations=[],
    )

    result = make_result(
        request=make_request(prompt_context=context),
        content="The sky is blue [S1].",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_validate_parses_multiple_markers_in_one_bracket() -> None:
    context = make_prompt_context(
        citations=[make_citation(citation_id="S1"), make_citation(citation_id="S2")],
    )

    result = make_result(
        request=make_request(prompt_context=context),
        content="Both facts are supported [S1, S2].",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_validate_ignores_non_identifier_bracketed_tokens() -> None:
    context = make_prompt_context(citations=[make_citation(citation_id="S1")])

    result = make_result(
        request=make_request(prompt_context=context),
        content="The answer is [1, 2, 3] and also cited [S1].",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
