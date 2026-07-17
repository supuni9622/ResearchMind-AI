"""
Unit tests for GenerationExecutionState.

Covers:
- Defaults (no result, not failed, no exception)
- Carrying a result marks a successful execution
- Carrying an exception marks a failed execution
"""

from __future__ import annotations

from app.ai.runtime.generation.orchestration.context import (
    GenerationExecutionContext,
)
from app.ai.runtime.generation.orchestration.state import (
    GenerationExecutionState,
)

from tests.unit.ai.runtime.generation.orchestration.factories import (
    make_request,
    make_result,
)


def test_defaults_are_unstarted() -> None:
    request = make_request()

    state = GenerationExecutionState(
        context=GenerationExecutionContext.for_request(request),
        request=request,
    )

    assert state.result is None
    assert state.failed is False
    assert state.exception is None


def test_carries_a_successful_result() -> None:
    request = make_request()

    result = make_result(request=request)

    state = GenerationExecutionState(
        context=GenerationExecutionContext.for_request(request),
        request=request,
        result=result,
    )

    assert state.result is result
    assert state.failed is False


def test_carries_a_failure() -> None:
    request = make_request()

    exc = RuntimeError("provider exploded")

    state = GenerationExecutionState(
        context=GenerationExecutionContext.for_request(request),
        request=request,
        failed=True,
        exception=exc,
    )

    assert state.failed is True
    assert state.exception is exc
