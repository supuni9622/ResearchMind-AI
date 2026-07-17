"""
Unit tests for RuntimeRegistry.

Covers:
- A fresh registry has no contracts/validators for any runtime
- register_contract / register_validator are keyed by RuntimeType
- validators_for only returns validators for the matching runtime
- contract_for returns None when nothing is registered for that runtime
- all_validators flattens contracts and standalone validators together
"""

from __future__ import annotations

from app.ai.runtime.generation.models import GenerationResult
from app.ai.runtime.generation.validation.models import ValidatorOutcome
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.ai.runtime.generation.validation.runtime.interfaces import (
    RuntimeContractInterface,
    RuntimeValidatorInterface,
)
from app.ai.runtime.generation.validation.runtime.registry import RuntimeRegistry


class _FakeContract(RuntimeContractInterface):
    def __init__(self, runtime: RuntimeType):
        self._runtime = runtime

    @property
    def runtime(self) -> RuntimeType:
        return self._runtime

    async def validate(self, result: GenerationResult) -> ValidatorOutcome:
        return ValidatorOutcome()


class _FakeValidator(RuntimeValidatorInterface):
    def __init__(self, name: str, runtime: RuntimeType):
        self._name = name
        self._runtime = runtime

    @property
    def name(self) -> str:
        return self._name

    @property
    def runtime(self) -> RuntimeType:
        return self._runtime

    async def validate(self, result: GenerationResult) -> ValidatorOutcome:
        return ValidatorOutcome()


def test_fresh_registry_has_nothing_registered() -> None:
    registry = RuntimeRegistry()

    assert registry.contract_for(RuntimeType.RESEARCH) is None
    assert registry.validators_for(RuntimeType.RESEARCH) == []
    assert registry.all_validators == []


def test_contracts_are_keyed_by_runtime() -> None:
    registry = RuntimeRegistry()

    research_contract = _FakeContract(RuntimeType.RESEARCH)
    planner_contract = _FakeContract(RuntimeType.PLANNER)

    registry.register_contract(research_contract)
    registry.register_contract(planner_contract)

    assert registry.contract_for(RuntimeType.RESEARCH) is research_contract
    assert registry.contract_for(RuntimeType.PLANNER) is planner_contract
    assert registry.contract_for(RuntimeType.AGENT) is None


def test_validators_are_keyed_by_runtime_and_order_is_preserved() -> None:
    registry = RuntimeRegistry()

    a = _FakeValidator("a", RuntimeType.RESEARCH)
    b = _FakeValidator("b", RuntimeType.RESEARCH)
    c = _FakeValidator("c", RuntimeType.PLANNER)

    registry.register_validator(a)
    registry.register_validator(b)
    registry.register_validator(c)

    assert registry.validators_for(RuntimeType.RESEARCH) == [a, b]
    assert registry.validators_for(RuntimeType.PLANNER) == [c]
    assert registry.validators_for(RuntimeType.AGENT) == []


def test_all_validators_flattens_contracts_and_standalone_validators() -> None:
    registry = RuntimeRegistry()

    contract = _FakeContract(RuntimeType.RESEARCH)
    validator = _FakeValidator("a", RuntimeType.PLANNER)

    registry.register_contract(contract)
    registry.register_validator(validator)

    assert registry.all_validators == [contract, validator]


def test_validators_for_returns_a_copy() -> None:
    registry = RuntimeRegistry()

    registry.register_validator(_FakeValidator("a", RuntimeType.RESEARCH))

    validators = registry.validators_for(RuntimeType.RESEARCH)
    validators.append(_FakeValidator("b", RuntimeType.RESEARCH))

    assert len(registry.validators_for(RuntimeType.RESEARCH)) == 1
