from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class BudgetPolicy(
    BaseModel,
):
    """
    Statically configured runtime limits (PRD §11) — set once per
    run/agent, not mutated during execution. `None` on any field means
    that limit is unbounded/not enforced.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    max_tokens: int | None = None

    max_cost_usd: float | None = None

    max_tool_calls: int | None = None

    max_iterations: int | None = None

    max_runtime_seconds: float | None = None


class ExecutionState(
    BaseModel,
):
    """
    Live accumulator describing a run's progress so far. The Guardrails
    Platform does not own or persist this state itself — a caller (e.g.
    a future agent runtime) tracks it and passes a fresh snapshot into
    `GuardrailService.evaluate_runtime()` on each check.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    tokens_used: int = 0

    cost_usd: float = 0.0

    tool_calls_made: int = 0

    iterations_completed: int = 0

    elapsed_seconds: float = 0.0

    visited_state_hashes: list[str] = Field(
        default_factory=list,
    )
    """
    A hash/signature per completed iteration (e.g. of the agent's
    plan+observations), appended by the caller. Used by
    `loop_detection.py` to spot repeated states — a duplicate hash means
    the run revisited a state it's already been in.
    """
