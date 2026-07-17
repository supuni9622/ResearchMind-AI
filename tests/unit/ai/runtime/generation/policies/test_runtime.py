"""
Unit tests for RuntimeValidationPolicy.

Covers:
- A failed runtime result never blocks by default (block_on_error=False)
- A failed runtime result blocks when block_on_error=True
- A valid runtime result never blocks, even with block_on_error=True
"""

from __future__ import annotations

from app.ai.runtime.generation.policies.runtime import RuntimeValidationPolicy
from app.ai.runtime.generation.validation.models import ValidationResult


def test_failed_result_does_not_block_by_default() -> None:
    policy = RuntimeValidationPolicy()

    assert policy.should_block(ValidationResult(valid=False)) is False


def test_failed_result_blocks_when_opted_in() -> None:
    policy = RuntimeValidationPolicy(block_on_error=True)

    assert policy.should_block(ValidationResult(valid=False)) is True


def test_valid_result_never_blocks_even_when_opted_in() -> None:
    policy = RuntimeValidationPolicy(block_on_error=True)

    assert policy.should_block(ValidationResult(valid=True)) is False
