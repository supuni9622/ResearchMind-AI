"""
Unit tests for the Validation Platform's core models.

Covers:
- ValidationReport.issues flattens every stage, in stage order
- ValidationReport.issues includes runtime_validation issues only when
  that stage is present (it's optional -- no runtime validators exist yet)
- ValidatorOutcome defaults to an empty, unscored outcome
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    ValidationStage,
    ValidatorOutcome,
)


def _issue(stage: ValidationStage, message: str) -> ValidationIssue:
    return ValidationIssue(
        validator="test",
        stage=stage,
        severity=ValidationSeverity.WARNING,
        message=message,
    )


def test_validator_outcome_defaults_to_empty_and_unscored() -> None:
    outcome = ValidatorOutcome()

    assert outcome.issues == []
    assert outcome.score is None


def test_report_issues_flattens_stages_in_order() -> None:
    report = ValidationReport(
        input_validation=ValidationResult(
            valid=True,
            issues=[_issue(ValidationStage.INPUT, "input issue")],
        ),
        output_validation=ValidationResult(
            valid=True,
            issues=[_issue(ValidationStage.OUTPUT, "output issue")],
        ),
        hallucination_validation=ValidationResult(
            valid=True,
            issues=[_issue(ValidationStage.HALLUCINATION, "hallucination issue")],
        ),
        valid=True,
    )

    messages = [issue.message for issue in report.issues]

    assert messages == ["input issue", "output issue", "hallucination issue"]


def test_report_issues_includes_runtime_stage_only_when_present() -> None:
    empty_result = ValidationResult(valid=True)

    report_without_runtime = ValidationReport(
        input_validation=empty_result,
        output_validation=empty_result,
        hallucination_validation=empty_result,
        runtime_validation=None,
        valid=True,
    )

    assert report_without_runtime.issues == []

    report_with_runtime = ValidationReport(
        input_validation=empty_result,
        output_validation=empty_result,
        hallucination_validation=empty_result,
        runtime_validation=ValidationResult(
            valid=True,
            issues=[_issue(ValidationStage.RUNTIME, "runtime issue")],
        ),
        valid=True,
    )

    assert [issue.message for issue in report_with_runtime.issues] == ["runtime issue"]
