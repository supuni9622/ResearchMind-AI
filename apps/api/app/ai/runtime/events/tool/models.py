from __future__ import annotations

from enum import StrEnum


class ToolEventType(StrEnum):
    """
    Reserved for the future Tool Runtime.

    Nothing in the Streaming Platform emits these today — no Tool Runtime
    exists yet. Defined ahead of time so that runtime, once built, only
    needs to import this enum rather than modify shared platform code (see
    ADR-028's Layer 3 — Runtime Events).
    """

    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
