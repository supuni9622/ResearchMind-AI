"""
Adversarial dataset: prompt injection, PII, and off-scope cases
(EVALUATION_PLAN.md §9, §18 Level 1).

Runs the real `PromptInjectionGuardrail`/`PiiDetectionGuardrail`/
`ScopeValidationGuardrail` (input stage) and `ContextSanitizationGuardrail`
(retrieval stage, RAG-borne injection) against
`datasets/adversarial/adversarial_cases.json` via
`benchmarks/guardrails/adversarial_runner.py`. No guardrail logic is
mocked -- only the `GenerationRequest`/`ContextChunk` fixtures the cases
run through are constructed directly.

`test_jailbreaks.py` covers the JAILBREAK and CITATION_INTEGRITY
categories from the same dataset, plus the dataset-level contract checks
(size, category coverage, the "at least one case evades detection"
acceptance criterion).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.ai.guardrails.enums import GuardrailCategory

from benchmarks.guardrails.adversarial_dataset import (
    AdversarialCase,
    load_adversarial_dataset,
)
from benchmarks.guardrails.adversarial_runner import run_case

DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "datasets" / "adversarial" / "adversarial_cases.json"
)

_TARGET_CATEGORIES = {
    GuardrailCategory.PROMPT_INJECTION,
    GuardrailCategory.PII,
    GuardrailCategory.SCOPE,
}


def _cases() -> list[AdversarialCase]:
    dataset = load_adversarial_dataset(DATASET_PATH)
    return [case for case in dataset.cases if case.category in _TARGET_CATEGORIES]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _cases(), ids=lambda case: case.case_id)
async def test_case_matches_its_recorded_expectation(case: AdversarialCase) -> None:
    """
    Every prompt-injection/PII/scope case's `expected_detected`/
    `expected_category`/`expected_severity` was empirically verified
    against the live guardrails before being committed to the dataset
    (see the dataset's own `notes` field and
    EVALUATION_IMPLEMENTATION_TRACKER.md E15) -- this test re-verifies
    that on every run, so a future guardrail regex change that silently
    changes detection behavior is caught here.
    """

    result = await run_case(case)

    assert result.matches_expectation, (
        f"{case.case_id}: expected detected={case.expected_detected}, got {result.detected} "
        f"(issues: {[issue.code for issue in result.issues]})"
    )

    if case.expected_detected:
        matching = [issue for issue in result.issues if issue.category == case.expected_category]
        assert matching, f"{case.case_id}: expected category {case.expected_category} not raised"

        if case.expected_severity is not None:
            assert any(issue.severity == case.expected_severity for issue in matching), (
                f"{case.case_id}: expected severity {case.expected_severity}, "
                f"got {[issue.severity for issue in matching]}"
            )


@pytest.mark.asyncio
async def test_direct_instruction_override_is_flagged_as_prompt_injection_not_jailbreak() -> None:
    """
    A single instruction-override trigger stays PROMPT_INJECTION/WARNING;
    it only escalates to JAILBREAK when combined with a second trigger
    (jb-3) or a jailbreak-specific keyword (jb-1/jb-2) -- see
    test_jailbreaks.py. Named explicitly since this distinction is easy
    to get wrong when reasoning about the guardrail from the outside.
    """

    dataset = load_adversarial_dataset(DATASET_PATH)
    case = next(case for case in dataset.cases if case.case_id == "pi-1")

    result = await run_case(case)

    assert result.detected
    assert all(issue.category != GuardrailCategory.JAILBREAK for issue in result.issues)


@pytest.mark.asyncio
async def test_rag_borne_injection_in_a_retrieved_chunk_is_flagged() -> None:
    """
    Explicit regression test for the retrieval-stage vector -- a
    malicious instruction embedded in an uploaded/retrieved document,
    not the user's own prompt (EVALUATION_PLAN.md §9's "prompt injection
    in an uploaded document" MVP requirement).
    """

    dataset = load_adversarial_dataset(DATASET_PATH)
    case = next(case for case in dataset.cases if case.case_id == "pi-5")

    result = await run_case(case)

    assert result.detected
    assert any(issue.category == GuardrailCategory.PROMPT_INJECTION for issue in result.issues)


@pytest.mark.asyncio
async def test_pii_detection_warns_but_never_blocks() -> None:
    dataset = load_adversarial_dataset(DATASET_PATH)
    case = next(case for case in dataset.cases if case.case_id == "pii-1")

    result = await run_case(case)

    assert result.detected
    assert all(
        issue.severity.value != "error"
        for issue in result.issues
        if issue.category == GuardrailCategory.PII
    )
