from __future__ import annotations

from enum import StrEnum


class ResearchEventType(StrEnum):
    """
    Reserved for the future Research Runtime.

    Nothing in the Streaming Platform emits these today — no Research
    Runtime exists yet. Defined ahead of time so that runtime, once built,
    only needs to import this enum rather than modify shared platform code
    (see ADR-028's Layer 3 — Runtime Events).
    """

    RESEARCH_STARTED = "research_started"
    RESEARCH_COMPLETED = "research_completed"

    PLANNER_STARTED = "planner_started"
    PLANNER_COMPLETED = "planner_completed"

    RETRIEVAL_STARTED = "retrieval_started"
    RETRIEVAL_COMPLETED = "retrieval_completed"

    REPORT_STARTED = "report_started"
    REPORT_COMPLETED = "report_completed"
