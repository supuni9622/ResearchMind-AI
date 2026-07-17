from __future__ import annotations

from enum import StrEnum


class EventCategory(StrEnum):
    """
    Which domain a StreamEvent belongs to.

    Distinct from `StreamEvent.type`, which is a free-form string owned by
    whichever domain emitted the event (see runtime/events/<domain>/models.py).
    `category` is what lets a generic consumer (frontend, observability)
    route/group events without knowing every domain's specific type values.
    """

    GENERATION = "generation"
    RESEARCH = "research"
    AGENT = "agent"
    TOOL = "tool"


class CoreEventType(StrEnum):
    """
    The only event-type enum the canonical StreamEvent model depends on.

    Every Layer 3 runtime (research/agent/tool/...) defines its own
    event-type enum instead of adding members here — see ADR-028's
    "Layer 2 — Canonical Stream Events" section for why a single shared
    enum across runtimes was rejected.
    """

    START = "start"
    TOKEN = "token"
    THINKING = "thinking"
    COMPLETE = "complete"
    ERROR = "error"
