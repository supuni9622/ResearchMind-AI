from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import RuntimeGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.runtime.execution_limits import BudgetPolicy, ExecutionState


class LoopDetectionGuardrail(
    RuntimeGuardrailInterface,
):
    """
    Foundation depth (PRD §11/§21) but a real, cheap algorithm rather
    than a no-op stub: flags a run that exceeded its iteration budget,
    and flags a run that revisited a state it's already been in (a
    repeated entry in `ExecutionState.visited_state_hashes` -- the
    caller is expected to append one hash per completed iteration).

    `max_depth` is a local constructor parameter rather than a new
    `BudgetPolicy` field, since no other guardrail needs it yet --
    avoids widening a shared model for a single consumer.
    """

    def __init__(
        self,
        *,
        max_depth: int | None = None,
    ) -> None:
        self._max_depth = max_depth

    @property
    def name(
        self,
    ) -> str:
        return "loop_detection"

    async def check(
        self,
        state: ExecutionState,
        policy: BudgetPolicy,
    ) -> list[GuardrailIssue]:

        issues: list[GuardrailIssue] = []

        if policy.max_iterations is not None and state.iterations_completed > policy.max_iterations:
            issues.append(
                GuardrailIssue(
                    code="max_iterations_exceeded",
                    severity=GuardrailSeverity.ERROR,
                    category=GuardrailCategory.LOOP,
                    message=(
                        f"Completed {state.iterations_completed} iterations, "
                        f"exceeding the limit of {policy.max_iterations}."
                    ),
                    metadata={
                        "iterations_completed": state.iterations_completed,
                        "max_iterations": policy.max_iterations,
                    },
                )
            )

        if self._max_depth is not None and state.iterations_completed > self._max_depth:
            issues.append(
                GuardrailIssue(
                    code="max_depth_exceeded",
                    severity=GuardrailSeverity.ERROR,
                    category=GuardrailCategory.LOOP,
                    message=(
                        f"Depth {state.iterations_completed} exceeds the "
                        f"configured max_depth of {self._max_depth}."
                    ),
                    metadata={"depth": state.iterations_completed, "max_depth": self._max_depth},
                )
            )

        repeated = self._find_repeated_hash(state.visited_state_hashes)

        if repeated is not None:
            issues.append(
                GuardrailIssue(
                    code="repeated_state_detected",
                    severity=GuardrailSeverity.ERROR,
                    category=GuardrailCategory.LOOP,
                    message=f"Run revisited a previously-seen state: {repeated}.",
                    metadata={"repeated_state_hash": repeated},
                )
            )

        return issues

    @staticmethod
    def _find_repeated_hash(
        hashes: list[str],
    ) -> str | None:

        seen: set[str] = set()

        for state_hash in hashes:
            if state_hash in seen:
                return state_hash

            seen.add(state_hash)

        return None
