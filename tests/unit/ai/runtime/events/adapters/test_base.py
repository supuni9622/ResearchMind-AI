"""
Unit tests for GenericStreamChunkAdapter.

Covers:
- StreamChunk -> StreamEvent field mapping (content, metadata, type)
- category is always GENERATION (the only category any provider emits
  through this adapter today)
- session_id/request_id pass through when given, default to None otherwise
"""

from __future__ import annotations

from uuid import uuid4

from app.ai.runtime.events.adapters.base import GenericStreamChunkAdapter
from app.ai.runtime.events.enums import EventCategory
from app.ai.runtime.generation.models import StreamChunk, StreamEventType


def test_to_stream_event_maps_content_and_type() -> None:
    adapter = GenericStreamChunkAdapter()

    chunk = StreamChunk(event=StreamEventType.TOKEN, content="hello")

    event = adapter.to_stream_event(chunk)

    assert event.type == StreamEventType.TOKEN.value
    assert event.content == "hello"
    assert event.category == EventCategory.GENERATION


def test_to_stream_event_carries_metadata_through() -> None:
    adapter = GenericStreamChunkAdapter()

    chunk = StreamChunk(
        event=StreamEventType.ERROR,
        metadata={"finish_reason": "content_filter"},
    )

    event = adapter.to_stream_event(chunk)

    assert event.metadata == {"finish_reason": "content_filter"}


def test_to_stream_event_passes_through_session_and_request_ids() -> None:
    adapter = GenericStreamChunkAdapter()

    session_id = uuid4()
    request_id = uuid4()

    event = adapter.to_stream_event(
        StreamChunk(event=StreamEventType.START),
        session_id=session_id,
        request_id=request_id,
    )

    assert event.session_id == session_id
    assert event.request_id == request_id


def test_to_stream_event_defaults_ids_to_none() -> None:
    adapter = GenericStreamChunkAdapter()

    event = adapter.to_stream_event(StreamChunk(event=StreamEventType.COMPLETED))

    assert event.session_id is None
    assert event.request_id is None
