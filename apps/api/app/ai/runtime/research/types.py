"""Minimal, framework-independent contracts for the Research Runtime."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResearchRuntimeStatus(StrEnum):
    CREATED = "created"
    INITIALIZED = "initialized"
    COMPLETED = "completed"


class ResearchRunStatus(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    RESEARCHING = "researching"
    REVIEWING = "reviewing"
    SYNTHESIZING = "synthesizing"
    PAUSED = "paused"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_PLAN_APPROVAL = "awaiting_plan_approval"
    COMPLETED = "completed"
    COMPLETED_WITH_LIMITATIONS = "completed_with_limitations"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ResearchProposalStatus(StrEnum):
    PROPOSING = "proposing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    CANCELLED = "cancelled"


TERMINAL_RESEARCH_RUN_STATUSES = frozenset(
    {
        ResearchRunStatus.COMPLETED.value,
        ResearchRunStatus.COMPLETED_WITH_LIMITATIONS.value,
        ResearchRunStatus.CANCELLED.value,
        ResearchRunStatus.FAILED.value,
    }
)


class ResearchRunDispatchStatus(StrEnum):
    """Durable outbox state; distinct from the public run lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


class ResearchRuntimeRequest(BaseModel):
    """Internal request contract for the deterministic Phase 1 graph."""

    model_config = ConfigDict(extra="forbid")

    research_run_id: UUID
    graph_thread_id: str = Field(min_length=1, max_length=255)
    owner_id: UUID
    pause_after_initialize: bool = False
