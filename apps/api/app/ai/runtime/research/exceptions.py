"""Classified Research Runtime execution failures, distinct from generic errors."""

from __future__ import annotations


class ResearchRunCancelledError(RuntimeError):
    """Raised inside the graph when a user-requested cancellation is observed."""


class ResearchRunBudgetExceededError(RuntimeError):
    """Raised when a run exceeds its bounded duration or cost policy."""


class ResearchReportRejectedError(RuntimeError):
    """Raised when the user rejects the final report at its approval checkpoint."""


class ResearchPlanRejectedError(RuntimeError):
    """Raised when the plan-approval interrupt resumes with a malformed
    decision payload -- a real rejection does not raise this (see
    `route_after_plan_approval` in `multi_wave_research.py`)."""
