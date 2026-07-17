"""
Unit tests for RuntimeValidationService.

Covers:
- A request with no `runtime` set skips the stage entirely (valid,
  no issues, no score)
- The registered contract for the request's runtime runs and its
  issues are stamped with ValidationStage.RUNTIME
- Standalone validators registered for that runtime also run,
  alongside the contract
- Only the contract/validators for the *matching* runtime run — a
  contract registered for a different runtime is ignored
- A crashing contract/validator becomes a WARNING issue rather than
  propagating
- Scores from multiple outcomes are averaged
"""

from __future__ import annotations

import pytest
from app.ai.runtime.generation.models import GenerationResult
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationSeverity,
    ValidationStage,
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.ai.runtime.generation.validation.runtime.interfaces import (
    RuntimeContractInterface,
    RuntimeValidatorInterface,
)
from app.ai.runtime.generation.validation.runtime.registry import RuntimeRegistry
from app.ai.runtime.generation.validation.runtime.service import RuntimeValidationService

from tests.unit.ai.runtime.generation.validation.factories import make_request, make_result


class _FakeContract(RuntimeContractInterface):
    def __init__(
        self,
        runtime: RuntimeType,
        outcome: ValidatorOutcome | None = None,
        raises: bool = False,
    ):
        self._runtime = runtime
        self._outcome = outcome or ValidatorOutcome()
        self._raises = raises

    @property
    def runtime(self) -> RuntimeType:
        return self._runtime

    async def validate(self, result: GenerationResult) -> ValidatorOutcome:
        if self._raises:
            raise RuntimeError("boom")
        return self._outcome


class _FakeValidator(RuntimeValidatorInterface):
    def __init__(
        self,
        name: str,
        runtime: RuntimeType,
        outcome: ValidatorOutcome | None = None,
        raises: bool = False,
    ):
        self._name = name
        self._runtime = runtime
        self._outcome = outcome or ValidatorOutcome()
        self._raises = raises

    @property
    def name(self) -> str:
        return self._name

    @property
    def runtime(self) -> RuntimeType:
        return self._runtime

    async def validate(self, result: GenerationResult) -> ValidatorOutcome:
        if self._raises:
            raise RuntimeError("boom")
        return self._outcome


def _issue(severity: ValidationSeverity, message: str = "issue") -> ValidationIssue:
    return ValidationIssue(validator="fake", severity=severity, message=message)


async def test_no_runtime_set_skips_the_stage() -> None:
    registry = RuntimeRegistry()
    registry.register_contract(_FakeContract(RuntimeType.RESEARCH))

    service = RuntimeValidationService(registry)

    result = make_result(request=make_request(runtime=None))

    outcome = await service.validate(result)

    assert outcome.valid is True
    assert outcome.issues == []
    assert outcome.score is None


async def test_matching_contract_runs_and_issues_are_stamped() -> None:
    registry = RuntimeRegistry()
    registry.register_contract(
        _FakeContract(
            RuntimeType.RESEARCH,
            ValidatorOutcome(issues=[_issue(ValidationSeverity.ERROR)]),
        )
    )

    service = RuntimeValidationService(registry)

    result = make_result(request=make_request(runtime=RuntimeType.RESEARCH))

    outcome = await service.validate(result)

    assert outcome.valid is False
    assert len(outcome.issues) == 1
    assert outcome.issues[0].stage == ValidationStage.RUNTIME


async def test_contract_for_a_different_runtime_is_ignored() -> None:
    registry = RuntimeRegistry()
    registry.register_contract(
        _FakeContract(
            RuntimeType.PLANNER,
            ValidatorOutcome(issues=[_issue(ValidationSeverity.ERROR)]),
        )
    )

    service = RuntimeValidationService(registry)

    result = make_result(request=make_request(runtime=RuntimeType.RESEARCH))

    outcome = await service.validate(result)

    assert outcome.valid is True
    assert outcome.issues == []


async def test_standalone_validators_run_alongside_the_contract() -> None:
    registry = RuntimeRegistry()
    registry.register_contract(_FakeContract(RuntimeType.RESEARCH, ValidatorOutcome(score=0.8)))
    registry.register_validator(
        _FakeValidator("extra", RuntimeType.RESEARCH, ValidatorOutcome(score=0.4))
    )

    service = RuntimeValidationService(registry)

    result = make_result(request=make_request(runtime=RuntimeType.RESEARCH))

    outcome = await service.validate(result)

    assert outcome.valid is True
    assert outcome.score == pytest.approx(0.6)


async def test_crashing_contract_becomes_a_warning() -> None:
    registry = RuntimeRegistry()
    registry.register_contract(_FakeContract(RuntimeType.RESEARCH, raises=True))

    service = RuntimeValidationService(registry)

    result = make_result(request=make_request(runtime=RuntimeType.RESEARCH))

    outcome = await service.validate(result)

    assert outcome.valid is True
    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING
    assert "crashed" in outcome.issues[0].message


async def test_crashing_validator_does_not_stop_the_contract_from_running() -> None:
    registry = RuntimeRegistry()
    registry.register_contract(_FakeContract(RuntimeType.RESEARCH, ValidatorOutcome(score=1.0)))
    registry.register_validator(_FakeValidator("crasher", RuntimeType.RESEARCH, raises=True))

    service = RuntimeValidationService(registry)

    result = make_result(request=make_request(runtime=RuntimeType.RESEARCH))

    outcome = await service.validate(result)

    assert outcome.valid is True
    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING
    assert outcome.score == 1.0
