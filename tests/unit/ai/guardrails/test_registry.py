"""
Unit tests for guardrails/registry.py.

Covers:
- register/list preserve registration order, per stage
- each stage's list is isolated from the others
- list properties return copies (mutating the returned list doesn't
  affect the registry)
"""

from __future__ import annotations

from app.ai.guardrails.interfaces import InputGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.registry import GuardrailRegistry
from app.ai.runtime.generation.models import GenerationRequest


class _FakeInputGuardrail(InputGuardrailInterface):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def check(self, request: GenerationRequest) -> list[GuardrailIssue]:
        return []


def test_register_and_list_preserve_order() -> None:
    registry = GuardrailRegistry()

    registry.register_input_guardrail(_FakeInputGuardrail("a"))
    registry.register_input_guardrail(_FakeInputGuardrail("b"))

    assert [g.name for g in registry.input_guardrails] == ["a", "b"]


def test_stages_are_isolated() -> None:
    registry = GuardrailRegistry()

    registry.register_input_guardrail(_FakeInputGuardrail("only-input"))

    assert registry.retrieval_guardrails == []
    assert registry.generation_guardrails == []
    assert registry.runtime_guardrails == []


def test_list_property_returns_a_copy() -> None:
    registry = GuardrailRegistry()

    registry.register_input_guardrail(_FakeInputGuardrail("a"))

    guardrails = registry.input_guardrails
    guardrails.append(_FakeInputGuardrail("b"))

    assert [g.name for g in registry.input_guardrails] == ["a"]
