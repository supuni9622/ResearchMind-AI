from __future__ import annotations

from app.ai.guardrails.policies.regeneration_policy import RegenerationPolicy


def test_defaults_regenerate_on_both() -> None:
    policy = RegenerationPolicy()

    assert policy.regenerate_on_hallucination is True
    assert policy.regenerate_on_schema_failure is True


def test_flags_are_independently_configurable() -> None:
    policy = RegenerationPolicy(regenerate_on_hallucination=False)

    assert policy.regenerate_on_hallucination is False
    assert policy.regenerate_on_schema_failure is True
