"""
Unit tests for ContextValidator.

Covers:
- Clean context (no duplicates, no empty chunks, consistent citations) -> no issues
- A chunk with empty/whitespace-only content -> WARNING
- Two chunks sharing the same chunk_id -> WARNING
- A chunk's citation_id not present in prompt_context.citations -> WARNING
- Empty chunks list entirely -> no issues (nothing to flag; the hard
  "context is empty" gate lives in GenerationService, not here)
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.input.context_validation import ContextValidator
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidationSeverity,
)

from tests.unit.ai.runtime.generation.validation.factories import (
    make_chunk,
    make_citation,
    make_prompt_context,
    make_request,
)

validator = ContextValidator()
context = InputValidationContext()


async def test_validate_passes_clean_context() -> None:
    prompt_context = make_prompt_context(
        chunks=[make_chunk(citation_id="S1")],
        citations=[make_citation(citation_id="S1")],
    )

    request = make_request(prompt_context=prompt_context)

    outcome = await validator.validate(request, context)

    assert outcome.issues == []


async def test_validate_warns_on_empty_chunk_content() -> None:
    prompt_context = make_prompt_context(chunks=[make_chunk(content="   ", citation_id=None)])

    request = make_request(prompt_context=prompt_context)

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING
    assert "empty content" in outcome.issues[0].message


async def test_validate_warns_on_duplicate_chunk_ids() -> None:
    from uuid import uuid4

    shared_id = uuid4()

    prompt_context = make_prompt_context(
        chunks=[
            make_chunk(chunk_id=shared_id, citation_id=None),
            make_chunk(chunk_id=shared_id, citation_id=None),
        ],
    )

    request = make_request(prompt_context=prompt_context)

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert "appear more than once" in outcome.issues[0].message


async def test_validate_warns_on_orphaned_chunk_citation() -> None:
    prompt_context = make_prompt_context(
        chunks=[make_chunk(citation_id="S1")],
        citations=[],
    )

    request = make_request(prompt_context=prompt_context)

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].details["orphaned_citation_ids"] == ["S1"]


async def test_validate_passes_when_chunks_are_empty() -> None:
    prompt_context = make_prompt_context(chunks=[], citations=[])

    request = make_request(prompt_context=prompt_context)

    outcome = await validator.validate(request, context)

    assert outcome.issues == []
