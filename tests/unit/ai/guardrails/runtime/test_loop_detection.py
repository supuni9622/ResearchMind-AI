from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.runtime.loop_detection import LoopDetectionGuardrail

from tests.unit.ai.guardrails.factories import make_budget_policy, make_execution_state


async def test_no_issues_when_within_limits_and_no_repeats() -> None:
    guardrail = LoopDetectionGuardrail()

    issues = await guardrail.check(
        make_execution_state(iterations_completed=2, visited_state_hashes=["a", "b"]),
        make_budget_policy(max_iterations=10),
    )

    assert issues == []


async def test_exceeding_max_iterations_errors() -> None:
    guardrail = LoopDetectionGuardrail()

    issues = await guardrail.check(
        make_execution_state(iterations_completed=15),
        make_budget_policy(max_iterations=10),
    )

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.ERROR
    assert issues[0].category == GuardrailCategory.LOOP
    assert issues[0].code == "max_iterations_exceeded"


async def test_repeated_state_hash_errors() -> None:
    guardrail = LoopDetectionGuardrail()

    issues = await guardrail.check(
        make_execution_state(visited_state_hashes=["a", "b", "a"]),
        make_budget_policy(),
    )

    assert len(issues) == 1
    assert issues[0].code == "repeated_state_detected"
    assert issues[0].metadata["repeated_state_hash"] == "a"


async def test_local_max_depth_is_independent_of_budget_policy() -> None:
    guardrail = LoopDetectionGuardrail(max_depth=3)

    issues = await guardrail.check(
        make_execution_state(iterations_completed=5),
        make_budget_policy(),  # no max_iterations set
    )

    assert len(issues) == 1
    assert issues[0].code == "max_depth_exceeded"
