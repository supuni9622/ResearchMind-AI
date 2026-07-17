from __future__ import annotations

from enum import StrEnum


class AgentEventType(StrEnum):
    """
    Reserved for the future Agent Runtime.

    Nothing in the Streaming Platform emits these today — no Agent Runtime
    exists yet. Defined ahead of time so that runtime, once built, only
    needs to import this enum rather than modify shared platform code (see
    ADR-028's Layer 3 — Runtime Events).
    """

    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"

    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"

    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"

    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
