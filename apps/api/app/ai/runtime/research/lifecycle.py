"""Research-run lifecycle policy, kept outside LangGraph nodes."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from app.ai.runtime.research.types import ResearchRunStatus
from app.models.research_run import ResearchRun

logger = structlog.get_logger()

_ALLOWED_TRANSITIONS: dict[ResearchRunStatus, set[ResearchRunStatus]] = {
    ResearchRunStatus.CREATED: {
        ResearchRunStatus.PLANNING,
        ResearchRunStatus.CANCELLED,
        ResearchRunStatus.FAILED,
    },
    ResearchRunStatus.PLANNING: {
        ResearchRunStatus.RESEARCHING,
        ResearchRunStatus.PAUSED,
        ResearchRunStatus.AWAITING_APPROVAL,
        ResearchRunStatus.CANCELLED,
        ResearchRunStatus.FAILED,
    },
    ResearchRunStatus.RESEARCHING: {
        ResearchRunStatus.REVIEWING,
        ResearchRunStatus.PAUSED,
        ResearchRunStatus.AWAITING_APPROVAL,
        ResearchRunStatus.AWAITING_PLAN_APPROVAL,
        ResearchRunStatus.AWAITING_WEB_SEARCH_APPROVAL,
        ResearchRunStatus.CANCELLED,
        ResearchRunStatus.FAILED,
    },
    ResearchRunStatus.REVIEWING: {
        ResearchRunStatus.SYNTHESIZING,
        ResearchRunStatus.RESEARCHING,
        ResearchRunStatus.COMPLETED_WITH_LIMITATIONS,
        ResearchRunStatus.CANCELLED,
        ResearchRunStatus.FAILED,
    },
    ResearchRunStatus.SYNTHESIZING: {
        ResearchRunStatus.COMPLETED,
        ResearchRunStatus.COMPLETED_WITH_LIMITATIONS,
        ResearchRunStatus.CANCELLED,
        ResearchRunStatus.FAILED,
    },
    ResearchRunStatus.PAUSED: {
        ResearchRunStatus.PLANNING,
        ResearchRunStatus.RESEARCHING,
        ResearchRunStatus.CANCELLED,
    },
    ResearchRunStatus.AWAITING_APPROVAL: {
        ResearchRunStatus.RESEARCHING,
        ResearchRunStatus.CANCELLED,
    },
    ResearchRunStatus.AWAITING_PLAN_APPROVAL: {
        ResearchRunStatus.RESEARCHING,
        ResearchRunStatus.CANCELLED,
    },
    ResearchRunStatus.AWAITING_WEB_SEARCH_APPROVAL: {
        ResearchRunStatus.RESEARCHING,
        ResearchRunStatus.CANCELLED,
    },
    ResearchRunStatus.COMPLETED: set(),
    ResearchRunStatus.COMPLETED_WITH_LIMITATIONS: set(),
    ResearchRunStatus.CANCELLED: set(),
    # The sole legal exit from FAILED: an explicit user-triggered retry
    # (ResearchRunService.retry_run) resuming from the run's last LangGraph
    # checkpoint. Not reachable via any automatic path.
    ResearchRunStatus.FAILED: {ResearchRunStatus.RESEARCHING},
}


def transition_run(
    run: ResearchRun,
    *,
    target: ResearchRunStatus,
    phase: str | None = None,
) -> None:
    """Apply a validated public lifecycle transition to a persistent run."""

    current = ResearchRunStatus(run.status)
    if target not in _ALLOWED_TRANSITIONS[current]:
        logger.warning(
            "research_runtime.lifecycle.transition_rejected",
            research_run_id=str(run.id),
            current_status=current.value,
            target_status=target.value,
        )
        raise ValueError(f"Cannot transition research run from '{current}' to '{target}'.")

    now = datetime.now(UTC)
    run.status = target.value
    run.current_phase = phase
    if target is not ResearchRunStatus.CREATED and run.started_at is None:
        run.started_at = now
    if target in {
        ResearchRunStatus.COMPLETED,
        ResearchRunStatus.COMPLETED_WITH_LIMITATIONS,
        ResearchRunStatus.CANCELLED,
        ResearchRunStatus.FAILED,
    }:
        run.completed_at = now

    logger.info(
        "research_runtime.lifecycle.transitioned",
        research_run_id=str(run.id),
        from_status=current.value,
        to_status=target.value,
        phase=phase,
    )
