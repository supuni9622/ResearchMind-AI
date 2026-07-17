from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.ai.runtime.events.enums import (
    EventCategory,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class StreamEvent(BaseModel):
    """
    Canonical, provider-independent event emitted by any runtime.

    `type` is a plain `str` rather than a value bound to one shared enum —
    each domain (generation/research/agent/tool) owns its own event-type
    enum under `runtime/events/<domain>/models.py` and populates `type`
    with its own values without this model ever importing them. See
    ADR-028's "Layer 2 — Canonical Stream Events" for the reasoning.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)

    session_id: UUID | None = None

    request_id: UUID | None = None

    parent_event_id: UUID | None = None

    category: EventCategory

    type: str

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    content: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
