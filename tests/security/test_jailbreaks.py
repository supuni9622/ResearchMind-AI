"""
Adversarial dataset: jailbreak and citation-integrity cases, plus the
dataset's own contract (EVALUATION_PLAN.md §9, §18 Level 1).

Runs the real `PromptInjectionGuardrail` (JAILBREAK category) and
`CitationIntegrityGuardrail` against
`datasets/adversarial/adversarial_cases.json` via
`benchmarks/guardrails/adversarial_runner.py`. See
`test_prompt_injection.py`'s module docstring for the PROMPT_INJECTION/
PII/SCOPE half of the same dataset.
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
    GuardrailCategory.JAILBREAK,
    GuardrailCategory.CITATION_INTEGRITY,
}


def _cases() -> list[AdversarialCase]:
    dataset = load_adversarial_dataset(DATASET_PATH)
    return [case for case in dataset.cases if case.category in _TARGET_CATEGORIES]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _cases(), ids=lambda case: case.case_id)
async def test_case_matches_its_recorded_expectation(case: AdversarialCase) -> None:
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
async def test_two_non_jailbreak_specific_triggers_still_escalate_to_jailbreak() -> None:
    """
    jb-3's real behavior, worth a named regression test on its own: an
    instruction-override trigger plus a system-prompt-extraction trigger
    -- neither individually jailbreak-specific -- together escalate the
    category from PROMPT_INJECTION to JAILBREAK. Easy to get wrong when
    reasoning about the guardrail from its docstring alone.
    """

    dataset = load_adversarial_dataset(DATASET_PATH)
    case = next(case for case in dataset.cases if case.case_id == "jb-3")

    result = await run_case(case)

    assert result.detected
    assert any(issue.category == GuardrailCategory.JAILBREAK for issue in result.issues)


@pytest.mark.asyncio
async def test_citation_attack_in_both_directions_is_caught() -> None:
    """
    Both `CitationIntegrityGuardrail` failure modes -- a citation
    claiming an unretrieved chunk, and a chunk claiming an unresolved
    citation -- are exercised (ci-1, ci-2).
    """

    dataset = load_adversarial_dataset(DATASET_PATH)
    citation_cases = [
        case for case in dataset.cases if case.category == GuardrailCategory.CITATION_INTEGRITY
    ]

    assert {case.attack_variant for case in citation_cases} == {
        "unknown_chunk_reference",
        "unresolved_citation",
    }

    for case in citation_cases:
        result = await run_case(case)
        assert result.detected, f"{case.case_id} should have been caught"


# -- Dataset-level contract ------------------------------------------------


@pytest.fixture(scope="module")
def adversarial_dataset():
    return load_adversarial_dataset(DATASET_PATH)


def test_dataset_meets_the_mvp_size_bar(adversarial_dataset) -> None:
    """EVALUATION_PLAN.md §9's MVP bar: a small (10-20 example) hand-built set."""

    assert 10 <= len(adversarial_dataset.cases) <= 20


def test_dataset_covers_input_and_retrieval_stages(adversarial_dataset) -> None:
    stages = {case.stage for case in adversarial_dataset.cases}

    assert {"input", "retrieval"} <= {stage.value for stage in stages}


def test_dataset_covers_every_real_guardrail_category(adversarial_dataset) -> None:
    """
    One case at minimum for every "Real" (non-stub) check this MVP
    scoped in: prompt_injection, pii, scope, jailbreak, citation_integrity.
    """

    covered = {case.category for case in adversarial_dataset.cases}

    assert covered == {
        GuardrailCategory.PROMPT_INJECTION,
        GuardrailCategory.PII,
        GuardrailCategory.SCOPE,
        GuardrailCategory.JAILBREAK,
        GuardrailCategory.CITATION_INTEGRITY,
    }


@pytest.mark.asyncio
async def test_at_least_one_case_evades_detection(adversarial_dataset) -> None:
    """
    EVALUATION_PLAN.md §9's own acceptance bar: "at least one case in
    the set currently passes through undetected (if none do, the set
    isn't adversarial enough yet)." Five cases here are deliberately
    evasive (paraphrase, Unicode homoglyphs, spelled-out PII, keyword-
    free jailbreak phrasing) -- this asserts that's still true, so a
    future guardrail improvement that starts catching everything
    prompts someone to add a *new*, harder evasion case rather than the
    check silently going stale.
    """

    results = [await run_case(case) for case in adversarial_dataset.cases]
    undetected = [result for result in results if not result.detected]

    assert undetected, (
        "Every adversarial case is now detected -- the set is no longer "
        "adversarial enough; add a new, harder evasion case."
    )


@pytest.mark.asyncio
async def test_every_case_in_the_dataset_matches_its_recorded_expectation(
    adversarial_dataset,
) -> None:
    """
    Full-dataset sweep, independent of the category-scoped parametrized
    tests above -- catches a case whose category doesn't fall into either
    test_prompt_injection.py's or this file's target set (a silent gap
    if a new category were ever added to the dataset without updating
    either file's `_TARGET_CATEGORIES`).
    """

    for case in adversarial_dataset.cases:
        result = await run_case(case)
        assert result.matches_expectation, case.case_id
