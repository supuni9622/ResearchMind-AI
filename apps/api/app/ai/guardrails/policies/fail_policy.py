from __future__ import annotations

from enum import StrEnum


class FailPolicy(StrEnum):
    """
    How `GuardrailService` should treat a guardrail check that crashes
    (PRD §12). A crashed check always produces a WARNING `GuardrailIssue`
    (see `GuardrailService._crash_issue`) — this policy only controls
    whether that WARNING is also allowed to block the stage.
    """

    FAIL_OPEN = "fail_open"
    """Default. A crashed check never blocks — the stage can still ALLOW
    or WARN based on whatever other issues were found."""

    FAIL_CLOSED = "fail_closed"
    """A crashed check blocks its stage outright, since the platform
    couldn't actually verify safety."""


def is_blocking_crash(
    policy: FailPolicy,
) -> bool:
    """Whether a crashed check should force `GuardrailResult.blocked=True`."""

    return policy == FailPolicy.FAIL_CLOSED
