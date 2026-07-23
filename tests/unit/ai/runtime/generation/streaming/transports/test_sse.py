from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
from app.ai.runtime.events.enums import EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.streaming.transports import sse as sse_transport


@pytest.mark.asyncio
async def test_sse_byte_stream_honors_a_shorter_max_duration_override(monkeypatch) -> None:
    """A caller-supplied ceiling (e.g. the research-run events route) must
    actually change when the stream is force-closed, not just the default.

    The heartbeat interval is shrunk so the duration check -- which only runs
    between `queue.get()` waits -- is reached quickly and deterministically,
    rather than depending on real 15s wall-clock heartbeat timing.
    """

    monkeypatch.setattr(sse_transport, "HEARTBEAT_INTERVAL_SECONDS", 0.01)

    async def never_completes() -> AsyncGenerator[StreamEvent, None]:
        await asyncio.Event().wait()
        yield StreamEvent(category=EventCategory.RESEARCH, type="unreachable")  # pragma: no cover

    chunks = [
        chunk
        async for chunk in sse_transport._sse_byte_stream(
            never_completes(), max_duration_seconds=0.05
        )
    ]

    assert any(b"Stream exceeded maximum duration" in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_sse_byte_stream_default_ceiling_is_unchanged() -> None:
    """Omitting the override must keep the existing chat/generation ceiling."""

    async def completes_immediately() -> AsyncGenerator[StreamEvent, None]:
        return
        yield  # pragma: no cover

    chunks = [chunk async for chunk in sse_transport._sse_byte_stream(completes_immediately())]

    assert not any(b"Stream exceeded maximum duration" in chunk for chunk in chunks)
