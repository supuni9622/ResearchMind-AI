from __future__ import annotations

from app.ai.guardrails.policies.fail_policy import FailPolicy, is_blocking_crash


def test_fail_open_does_not_block() -> None:
    assert is_blocking_crash(FailPolicy.FAIL_OPEN) is False


def test_fail_closed_blocks() -> None:
    assert is_blocking_crash(FailPolicy.FAIL_CLOSED) is True
