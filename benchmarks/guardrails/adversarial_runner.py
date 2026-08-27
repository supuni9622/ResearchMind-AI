"""
Adversarial case runner (EVALUATION_PLAN.md §9, MVP slice).

Dispatches each `AdversarialCase` to the real guardrail(s) for its stage
and runs it -- no mocking of guardrail logic itself; the only fakes
involved are `GenerationRequest`/`ContextChunk`/`Citation` fixture
construction (via `tests/unit/ai/guardrails/factories.py`'s existing
builders), matching how these guardrails are actually exercised in
production. Only the checks marked "Real" in
`docs/GUARDRAILS_EVALUATION.md`'s status table are dispatched here --
stub checks (toxicity, moderation, access_control, rate_limit) always
return `[]` unconditionally, so running adversarial cases against them
would only ever prove the stub is a stub, which is already documented
there; that's Wave 7's gap-filling work, not this dataset's job.
"""

from __future__ import annotations

from uuid import uuid4

from app.ai.guardrails.input.pii_detection import PiiDetectionGuardrail
from app.ai.guardrails.input.prompt_injection import PromptInjectionGuardrail
from app.ai.guardrails.input.scope_validation import ScopeValidationGuardrail
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.retrieval.citation_integrity import CitationIntegrityGuardrail
from app.ai.guardrails.retrieval.context_sanitization import ContextSanitizationGuardrail
from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.guardrails.create import create_context_guardrail_service
from app.ai.knowledge.context.models import ContextChunk, PromptContext
from app.ai.runtime.generation.models import GenerationRequest
from pydantic import BaseModel, ConfigDict

from benchmarks.guardrails.adversarial_dataset import AdversarialCase, PayloadLocation

_INPUT_GUARDRAILS = (
    PromptInjectionGuardrail(),
    PiiDetectionGuardrail(),
    ScopeValidationGuardrail(),
)


class AdversarialCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    detected: bool
    issues: list[GuardrailIssue]
    matches_expectation: bool


async def _run_input_case(case: AdversarialCase) -> list[GuardrailIssue]:
    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt=(case.payload if case.payload_location == PayloadLocation.USER_PROMPT else ""),
        system_prompt=(
            case.payload if case.payload_location == PayloadLocation.SYSTEM_PROMPT else None
        ),
    )

    issues: list[GuardrailIssue] = []
    for guardrail in _INPUT_GUARDRAILS:
        issues.extend(await guardrail.check(request))

    return issues


async def _run_retrieval_injection_case(case: AdversarialCase) -> list[GuardrailIssue]:
    guardrail = ContextSanitizationGuardrail(create_context_guardrail_service())
    chunk = ContextChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        filename="adversarial-document.pdf",
        owner_id="benchmark",
        chunk_index=0,
        content=case.payload,
        score=0.9,
    )

    return await guardrail.check([chunk])


async def _run_citation_attack_case(case: AdversarialCase) -> list[GuardrailIssue]:
    guardrail = CitationIntegrityGuardrail()
    retrieved_chunk_id = uuid4()

    retrieved_chunk = ContextChunk(
        chunk_id=retrieved_chunk_id,
        document_id=uuid4(),
        filename="real-document.pdf",
        owner_id="benchmark",
        chunk_index=0,
        content="Real, retrieved content.",
        score=0.9,
        citation_id="S1" if case.attack_variant == "unresolved_citation" else None,
    )

    if case.attack_variant == "unknown_chunk_reference":
        # The citation claims a chunk that was never actually retrieved.
        citation = Citation(
            citation_id="S1",
            filename="real-document.pdf",
            document_id=uuid4(),
            chunk_ids=[uuid4()],
        )
        chunks = [retrieved_chunk]
    elif case.attack_variant == "unresolved_citation":
        # The chunk claims a citation_id no Citation object provides.
        citation = Citation(
            citation_id="S2",
            filename="real-document.pdf",
            document_id=uuid4(),
            chunk_ids=[retrieved_chunk_id],
        )
        chunks = [retrieved_chunk]
    else:
        raise ValueError(f"Unknown citation attack_variant: {case.attack_variant!r}")

    return await guardrail.check_citations(chunks=chunks, citations=[citation])


async def run_case(case: AdversarialCase) -> AdversarialCaseResult:
    if case.payload_location == PayloadLocation.CITATION_ATTACK:
        issues = await _run_citation_attack_case(case)
    elif case.payload_location == PayloadLocation.RETRIEVED_CHUNK:
        issues = await _run_retrieval_injection_case(case)
    else:
        issues = await _run_input_case(case)

    detected = any(issue.category == case.category for issue in issues)

    matches_expectation = detected == case.expected_detected

    return AdversarialCaseResult(
        case_id=case.case_id,
        detected=detected,
        issues=issues,
        matches_expectation=matches_expectation,
    )


__all__ = [
    "AdversarialCaseResult",
    "run_case",
]
