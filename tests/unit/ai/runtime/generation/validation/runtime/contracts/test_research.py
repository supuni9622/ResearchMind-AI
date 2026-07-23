"""
Unit tests for ResearchRuntimeContract.

Covers:
- A fully compliant research output is valid with no issues
- A response with no findings and no cited sources produces the
  expected errors (reproducing the PRD §3 motivating example,
  {"abstract": "AI is important."})
- Every issue is tagged with the contract's own name, not the
  underlying check's name (PRD §21's report example)
- runtime/contract_name/name expose RuntimeType.RESEARCH / "research_contract"

Field names mirror `ResearchDraft`/`ResearchDraftSection`
(`app/ai/runtime/research/synthesis/models.py`), the actual
`output_model` the synthesis step requests.
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
    "abstract": "This is a sufficiently long research abstract for the contract.",
    "findings": [
        {"heading": "Background", "content": "supports the claim", "citation_ids": ["S1"]},
        {"heading": "Findings", "content": "supports the claim", "citation_ids": ["S1"]},
    ],
    "citation_ids": ["S1"],
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


async def test_trivial_output_fails_on_every_missing_requirement() -> None:
    contract = ResearchRuntimeContract()

    request = _request_with_known_citation()
    result = make_result(request=request, parsed_output={"abstract": "AI is important."})

    outcome = await contract.validate(result)

    assert outcome.issues != []
    messages = " ".join(issue.message for issue in outcome.issues)

    assert "findings" in messages
    assert "citation_ids" in messages


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
