"""
Unit tests for FailFastPolicy.

Covers:
- A valid input result never stops execution
- An invalid input result stops execution when stop_on_error=True (default)
- stop_on_error=False never stops execution, even for an invalid result
"""

from __future__ import annotations

from app.ai.runtime.generation.policies.fail_fast import FailFastPolicy
from app.ai.runtime.generation.validation.models import ValidationResult


def test_valid_result_never_stops() -> None:
    policy = FailFastPolicy()

    assert policy.should_stop(ValidationResult(valid=True)) is False


def test_invalid_result_stops_by_default() -> None:
    policy = FailFastPolicy()

    assert policy.should_stop(ValidationResult(valid=False)) is True


def test_stop_on_error_false_never_stops() -> None:
    policy = FailFastPolicy(stop_on_error=False)

    assert policy.should_stop(ValidationResult(valid=False)) is False
