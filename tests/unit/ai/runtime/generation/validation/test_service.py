"""
Unit tests for ValidationService.

Covers:
- validate_input aggregates issues/scores from every input validator and
  stamps ValidationStage.INPUT onto each issue
- validate_output / validate_hallucination do the same for their stages
- A validator that raises is converted into a WARNING "crashed" issue
  rather than propagating (and doesn't stop the remaining validators)
- validate() combines all three stages into a ValidationReport with a
  correctly aggregated `valid` and `overall_score`
- validator_names lists every registered validator across all stages
"""

from __future__ import annotations

from app.ai.runtime.generation.models import GenerationRequest, GenerationResult
from app.ai.runtime.generation.validation.interfaces import (
    InputValidatorInterface,
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidationIssue,
    ValidationSeverity,
    ValidationStage,
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.registry import ValidationRegistry
from app.ai.runtime.generation.validation.service import ValidationService

from tests.unit.ai.runtime.generation.validation.factories import make_request, make_result


class _FakeInputValidator(InputValidatorInterface):
    def __init__(self, name: str, outcome: ValidatorOutcome | None = None, raises: bool = False):
        self._name = name
        self._outcome = outcome or ValidatorOutcome()
        self._raises = raises

    @property
    def name(self) -> str:
        return self._name

    async def validate(
        self, request: GenerationRequest, context: InputValidationContext
    ) -> ValidatorOutcome:
        if self._raises:
            raise RuntimeError("boom")
        return self._outcome


class _FakeOutputValidator(OutputValidatorInterface):
    def __init__(self, name: str, outcome: ValidatorOutcome | None = None, raises: bool = False):
        self._name = name
        self._outcome = outcome or ValidatorOutcome()
        self._raises = raises

    @property
    def name(self) -> str:
        return self._name

    async def validate(self, result: GenerationResult) -> ValidatorOutcome:
        if self._raises:
            raise RuntimeError("boom")
        return self._outcome


def _issue(severity: ValidationSeverity, message: str = "issue") -> ValidationIssue:
    return ValidationIssue(validator="fake", severity=severity, message=message)


async def test_validate_input_aggregates_and_stamps_stage() -> None:
    registry = ValidationRegistry()
    registry.register_input_validator(
        _FakeInputValidator("a", ValidatorOutcome(issues=[_issue(ValidationSeverity.WARNING)]))
    )
    registry.register_input_validator(_FakeInputValidator("b", ValidatorOutcome(score=0.6)))

    service = ValidationService(registry=registry)

    result = await service.validate_input(make_request())

    assert result.valid is True
    assert len(result.issues) == 1
    assert result.issues[0].stage == ValidationStage.INPUT
    assert result.score == 0.6


async def test_validate_input_uses_default_context_when_none_given() -> None:
    registry = ValidationRegistry()
    registry.register_input_validator(_FakeInputValidator("a"))

    service = ValidationService(registry=registry)

    # Should not raise even though no InputValidationContext was passed.
    result = await service.validate_input(make_request())

    assert result.valid is True


async def test_validate_output_error_makes_result_invalid() -> None:
    registry = ValidationRegistry()
    registry.register_output_validator(
        _FakeOutputValidator("a", ValidatorOutcome(issues=[_issue(ValidationSeverity.ERROR)]))
    )

    service = ValidationService(registry=registry)

    result = await service.validate_output(make_result())

    assert result.valid is False
    assert result.issues[0].stage == ValidationStage.OUTPUT


async def test_crashing_validator_becomes_a_warning_and_others_still_run() -> None:
    registry = ValidationRegistry()
    registry.register_output_validator(_FakeOutputValidator("crasher", raises=True))
    registry.register_output_validator(_FakeOutputValidator("b", ValidatorOutcome(score=0.9)))

    service = ValidationService(registry=registry)

    result = await service.validate_output(make_result())

    # The crash produces a WARNING, not an ERROR, so overall validity
    # survives; the second validator's score still contributes.
    assert result.valid is True
    assert len(result.issues) == 1
    assert result.issues[0].severity == ValidationSeverity.WARNING
    assert "crashed" in result.issues[0].message
    assert result.score == 0.9


async def test_hallucination_stage_is_independent_of_output_stage() -> None:
    registry = ValidationRegistry()
    registry.register_output_validator(
        _FakeOutputValidator("out", ValidatorOutcome(issues=[_issue(ValidationSeverity.ERROR)]))
    )
    registry.register_hallucination_validator(
        _FakeOutputValidator("hallu", ValidatorOutcome(score=0.2))
    )

    service = ValidationService(registry=registry)

    hallucination_result = await service.validate_hallucination(make_result())

    assert hallucination_result.valid is True
    assert hallucination_result.score == 0.2


async def test_validate_builds_a_report_across_all_three_stages() -> None:
    registry = ValidationRegistry()
    registry.register_input_validator(_FakeInputValidator("in", ValidatorOutcome(score=1.0)))
    registry.register_output_validator(
        _FakeOutputValidator("out", ValidatorOutcome(issues=[_issue(ValidationSeverity.ERROR)]))
    )
    registry.register_hallucination_validator(
        _FakeOutputValidator("hallu", ValidatorOutcome(score=0.5))
    )

    service = ValidationService(registry=registry)

    request = make_request()
    result = make_result(request=request)

    report = await service.validate(request=request, result=result)

    assert report.input_validation.valid is True
    assert report.output_validation.valid is False
    assert report.hallucination_validation.valid is True
    assert report.valid is False  # output stage failing makes the whole report invalid
    assert report.overall_score is not None
    assert len(report.issues) == 1
    assert report.issues[0].stage == ValidationStage.OUTPUT


async def test_validator_names_lists_every_stage() -> None:
    registry = ValidationRegistry()
    registry.register_input_validator(_FakeInputValidator("in"))
    registry.register_output_validator(_FakeOutputValidator("out"))
    registry.register_hallucination_validator(_FakeOutputValidator("hallu"))

    service = ValidationService(registry=registry)

    assert service.validator_names == ["in", "out", "hallu"]


async def test_validate_input_accepts_explicit_context() -> None:
    seen_context: list[InputValidationContext] = []

    class RecordingValidator(_FakeInputValidator):
        async def validate(
            self, request: GenerationRequest, context: InputValidationContext
        ) -> ValidatorOutcome:
            seen_context.append(context)
            return ValidatorOutcome()

    registry = ValidationRegistry()
    registry.register_input_validator(RecordingValidator("recorder"))

    service = ValidationService(registry=registry)

    context = InputValidationContext(context_window=1234)

    await service.validate_input(make_request(), context)

    assert seen_context == [context]
