from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent


def make_events(started_at: datetime) -> list[StreamEvent]:
    return [
        StreamEvent(
            category=EventCategory.GENERATION,
            type=CoreEventType.START.value,
            timestamp=started_at,
        ),
        StreamEvent(
            category=EventCategory.GENERATION,
            type=CoreEventType.TOKEN.value,
            content="hel",
            timestamp=started_at + timedelta(milliseconds=50),
        ),
        StreamEvent(
            category=EventCategory.GENERATION,
            type=CoreEventType.TOKEN.value,
            content="lo",
            timestamp=started_at + timedelta(milliseconds=100),
        ),
        StreamEvent(
            category=EventCategory.GENERATION,
            type=CoreEventType.COMPLETE.value,
            timestamp=started_at + timedelta(milliseconds=150),
        ),
    ]


def utcnow() -> datetime:
    return datetime.now(UTC)
