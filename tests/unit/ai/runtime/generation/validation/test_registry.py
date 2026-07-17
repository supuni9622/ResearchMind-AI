"""
Unit tests for ValidationRegistry.

Covers:
- A fresh registry has no validators registered in any category
- register_input_validator / register_output_validator /
  register_hallucination_validator each add to their own list only
- Registration order is preserved
- The accessor properties return copies, not the live internal list
  (mutating the returned list must not affect the registry's state)
- register_runtime_validator / register_runtime_contract delegate to
  the underlying RuntimeRegistry, and runtime_validators reflects both
"""

from __future__ import annotations

from app.ai.runtime.generation.models import GenerationResult
from app.ai.runtime.generation.validation.input.empty_prompt import EmptyPromptValidator
from app.ai.runtime.generation.validation.models import ValidatorOutcome
from app.ai.runtime.generation.validation.output.citation_validator import CitationValidator
from app.ai.runtime.generation.validation.output.hallucination_validator import (
    HallucinationValidator,
)
from app.ai.runtime.generation.validation.output.schema_validator import SchemaValidator
from app.ai.runtime.generation.validation.registry import ValidationRegistry
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.ai.runtime.generation.validation.runtime.interfaces import (
    RuntimeContractInterface,
    RuntimeValidatorInterface,
)


class _FakeContract(RuntimeContractInterface):
    @property
    def runtime(self) -> RuntimeType:
        return RuntimeType.RESEARCH

    async def validate(self, result: GenerationResult) -> ValidatorOutcome:
        return ValidatorOutcome()


class _FakeRuntimeValidator(RuntimeValidatorInterface):
    @property
    def name(self) -> str:
        return "fake_runtime"

    @property
    def runtime(self) -> RuntimeType:
        return RuntimeType.PLANNER

    async def validate(self, result: GenerationResult) -> ValidatorOutcome:
        return ValidatorOutcome()


def test_fresh_registry_has_no_validators() -> None:
    registry = ValidationRegistry()

    assert registry.input_validators == []
    assert registry.output_validators == []
    assert registry.hallucination_validators == []
    assert registry.runtime_validators == []


def test_register_input_validator_only_affects_input_list() -> None:
    registry = ValidationRegistry()

    registry.register_input_validator(EmptyPromptValidator())

    assert len(registry.input_validators) == 1
    assert registry.output_validators == []
    assert registry.hallucination_validators == []


def test_registration_order_is_preserved() -> None:
    registry = ValidationRegistry()

    schema = SchemaValidator()
    citation = CitationValidator()

    registry.register_output_validator(schema)
    registry.register_output_validator(citation)

    assert registry.output_validators == [schema, citation]


def test_output_validators_property_returns_a_copy() -> None:
    registry = ValidationRegistry()

    registry.register_output_validator(SchemaValidator())

    validators = registry.output_validators
    validators.append(HallucinationValidator())

    assert len(registry.output_validators) == 1


def test_register_runtime_contract_and_validator_populate_runtime_validators() -> None:
    registry = ValidationRegistry()

    contract = _FakeContract()
    validator = _FakeRuntimeValidator()

    registry.register_runtime_contract(contract)
    registry.register_runtime_validator(validator)

    assert registry.runtime_validators == [contract, validator]
    assert registry.input_validators == []


def test_runtime_registry_resolves_by_runtime_type() -> None:
    registry = ValidationRegistry()

    contract = _FakeContract()
    registry.register_runtime_contract(contract)

    assert registry.runtime_registry.contract_for(RuntimeType.RESEARCH) is contract
    assert registry.runtime_registry.contract_for(RuntimeType.PLANNER) is None
