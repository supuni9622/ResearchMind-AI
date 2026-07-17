"""
Unit tests for ResearchRuntimeContract.

Covers:
- A fully compliant research output is valid with no issues
- A response with no citations, no evidence, and no sections produces
  the errors described by PRD §15's example ("no citations", "no
  evidence", "incomplete") -- reproducing the PRD §3 motivating example
  ({"summary": "AI is important."})
- Every issue is tagged with the contract's own name, not the
  underlying check's name (PRD §21's report example)
- A valid output's confidence score is reflected in the outcome score
- runtime/contract_name/name expose RuntimeType.RESEARCH / "research_contract"
"""

from __future__ import annotations

from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.runtime.contracts.research import (
    ResearchRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType

from tests.unit.ai.runtime.generation.validation.factories import (
    make_citation,
    make_prompt_context,
    make_request,
    make_result,
)

_COMPLIANT_PAYLOAD = {
    "summary": "This is a sufficiently long research summary for the contract.",
    "sections": [
        {"id": "sec-1", "title": "Background"},
        {"id": "sec-2", "title": "Findings"},
    ],
    "citations": ["S1"],
    "evidence": [{"content": "supports the claim", "citation_id": "S1", "section_id": "sec-2"}],
    "confidence": 0.8,
}


def _request_with_known_citation() -> GenerationRequest:
    prompt_context = make_prompt_context(citations=[make_citation(citation_id="S1")])
    return make_request(prompt_context=prompt_context)


async def test_contract_identity() -> None:
    contract = ResearchRuntimeContract()

    assert contract.runtime == RuntimeType.RESEARCH
    assert contract.contract_name == "research_contract"
    assert contract.name == "research_contract"


async def test_fully_compliant_output_is_valid() -> None:
    contract = ResearchRuntimeContract()

    request = _request_with_known_citation()
    result = make_result(request=request, parsed_output=dict(_COMPLIANT_PAYLOAD))

    outcome = await contract.validate(result)

    assert outcome.issues == []
    assert outcome.score == 0.8


async def test_trivial_output_fails_on_every_missing_requirement() -> None:
    contract = ResearchRuntimeContract()

    request = _request_with_known_citation()
    result = make_result(request=request, parsed_output={"summary": "AI is important."})

    outcome = await contract.validate(result)

    assert outcome.issues != []
    messages = " ".join(issue.message for issue in outcome.issues)

    assert "sections" in messages
    assert "citations" in messages
    assert "evidence" in messages
    assert "confidence" in messages


async def test_every_issue_is_tagged_with_the_contract_name() -> None:
    contract = ResearchRuntimeContract()

    request = _request_with_known_citation()
    result = make_result(request=request, parsed_output={})

    outcome = await contract.validate(result)

    assert outcome.issues
    assert all(issue.validator == "research_contract" for issue in outcome.issues)
    assert all(issue.severity == ValidationSeverity.ERROR for issue in outcome.issues)
    # Original check name preserved for debugging, even though `validator` is unified.
    assert all("check" in issue.details for issue in outcome.issues)
