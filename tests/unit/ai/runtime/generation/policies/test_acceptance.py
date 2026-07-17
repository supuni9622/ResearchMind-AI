"""
Unit tests for AcceptancePolicy.

Covers:
- No report and no parse failure -> ACCEPT
- Missing parsed_output on a structured request -> REGENERATE, regardless
  of the report
- A failing output stage -> REGENERATE by default
- regenerate_on_output_invalid=False leaves a failing output stage as ACCEPT
- A failing input stage is ACCEPT by default (reject_on_input_invalid=False)
- reject_on_input_invalid=True turns a failing input stage into REJECT
- A valid report -> ACCEPT
"""

from __future__ import annotations

from app.ai.runtime.generation.policies.acceptance import (
    AcceptanceDecision,
    AcceptancePolicy,
)
from app.ai.runtime.generation.validation.models import (
    ValidationReport,
    ValidationResult,
)


def _report(*, input_valid: bool = True, output_valid: bool = True) -> ValidationReport:
    return ValidationReport(
        input_validation=ValidationResult(valid=input_valid),
        output_validation=ValidationResult(valid=output_valid),
        hallucination_validation=ValidationResult(valid=True),
        valid=input_valid and output_valid,
    )


def test_no_report_and_no_parse_failure_accepts() -> None:
    policy = AcceptancePolicy()

    assert policy.decide(report=None) == AcceptanceDecision.ACCEPT


def test_missing_parsed_output_regenerates_regardless_of_report() -> None:
    policy = AcceptancePolicy()

    decision = policy.decide(report=_report(), parsed_output_missing=True)

    assert decision == AcceptanceDecision.REGENERATE


def test_failing_output_stage_regenerates_by_default() -> None:
    policy = AcceptancePolicy()

    decision = policy.decide(report=_report(output_valid=False))

    assert decision == AcceptanceDecision.REGENERATE


def test_regenerate_on_output_invalid_false_accepts_a_failing_output_stage() -> None:
    policy = AcceptancePolicy(regenerate_on_output_invalid=False)

    decision = policy.decide(report=_report(output_valid=False))

    assert decision == AcceptanceDecision.ACCEPT


def test_failing_input_stage_accepts_by_default() -> None:
    policy = AcceptancePolicy()

    decision = policy.decide(report=_report(input_valid=False))

    assert decision == AcceptanceDecision.ACCEPT


def test_reject_on_input_invalid_true_rejects_a_failing_input_stage() -> None:
    policy = AcceptancePolicy(reject_on_input_invalid=True)

    decision = policy.decide(report=_report(input_valid=False))

    assert decision == AcceptanceDecision.REJECT


def test_valid_report_accepts() -> None:
    policy = AcceptancePolicy()

    decision = policy.decide(report=_report())

    assert decision == AcceptanceDecision.ACCEPT
