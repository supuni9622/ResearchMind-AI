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
    RESEARCH_FAILED = "research_failed"

    RUNTIME_INITIALIZED = "research_runtime_initialized"
    RUNTIME_COMPLETED = "research_runtime_completed"

    PLANNER_STARTED = "planner_started"
    PLANNER_COMPLETED = "planner_completed"

    RETRIEVAL_STARTED = "retrieval_started"
    RETRIEVAL_COMPLETED = "retrieval_completed"

    EVIDENCE_STARTED = "evidence_started"
    EVIDENCE_COMPLETED = "evidence_completed"

    REVIEW_STARTED = "review_started"
    REVIEW_COMPLETED = "review_completed"

    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_COMPLETED = "synthesis_completed"

    REPORT_STARTED = "report_started"
    REPORT_COMPLETED = "report_completed"

    RESEARCH_PAUSED = "research_paused"
    RESEARCH_RESUMED = "research_resumed"
    RESEARCH_AWAITING_APPROVAL = "research_awaiting_approval"
    RESEARCH_AWAITING_PLAN_APPROVAL = "research_awaiting_plan_approval"
    RESEARCH_AWAITING_WEB_SEARCH_APPROVAL = "research_awaiting_web_search_approval"
    RESEARCH_CANCELLED = "research_cancelled"

    RESEARCH_WEB_SEARCH_STARTED = "research_web_search_started"
    RESEARCH_WEB_SEARCH_COMPLETED = "research_web_search_completed"
    RESEARCH_WEB_SEARCH_SKIPPED = "research_web_search_skipped"

    # Non-blocking, best-effort related-paper suggestion (Research
    # Intelligence MCP) fired once after the report is persisted -- never
    # gates the run, unlike the web-search approval checkpoint above.
    RESEARCH_RELATED_PAPERS_STARTED = "research_related_papers_started"
    RESEARCH_RELATED_PAPERS_COMPLETED = "research_related_papers_completed"
    RESEARCH_RELATED_PAPERS_SKIPPED = "research_related_papers_skipped"
