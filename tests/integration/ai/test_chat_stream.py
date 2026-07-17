"""
Integration tests for POST /api/v1/chat/stream.

Covers:
- Requires authentication (401 without a bearer token)
- A live stream is returned as `text/event-stream` SSE frames in order
- The completed turn is persisted (via ConversationService.append_turn)
  with the assembled content once the stream reaches COMPLETE

StreamingService and ConversationService are faked (like
_FakeRetrievalService in test_retrieval_filters.py) rather than run
against a live LLM provider or a real Postgres session shared across the
TestClient's independent event loop.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Iterator

import pytest
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest
from app.auth.dependencies import get_current_user
from app.dependencies.generation import get_conversation_service, get_streaming_service
from app.main import app
from app.models.conversation import Conversation
from app.models.user import User
from fastapi.testclient import TestClient

_OWNER_ID = uuid.uuid4()
_CONVERSATION_ID = uuid.uuid4()


def _fake_user() -> User:
    return User(
        id=_OWNER_ID,
        auth_provider="test",
        provider_user_id=str(_OWNER_ID),
        email="owner@example.com",
    )


class _FakeStreamingService:
    """Stands in for StreamingService -- yields a canned event sequence."""

    def __init__(self, events: list[StreamEvent]) -> None:
        self._events = events
        self.received_requests: list[GenerationRequest] = []

    async def stream_generate(
        self,
        *,
        request: GenerationRequest,
        provider: GenerationProvider | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        self.received_requests.append(request)

        for event in self._events:
            yield event


class _FakeConversationService:
    """Stands in for ConversationService -- records append_turn calls."""

    def __init__(self) -> None:
        self.appended_turns: list[dict] = []

    async def get_or_create(self, *, conversation_id, owner_id) -> Conversation:
        return Conversation(id=_CONVERSATION_ID, owner_id=owner_id)

    async def load_history(self, *, conversation_id, limit: int = 50) -> list:
        return []

    async def append_turn(
        self,
        *,
        conversation_id,
        user_prompt,
        assistant_content,
        provider=None,
        model=None,
    ) -> None:
        self.appended_turns.append(
            {
                "conversation_id": conversation_id,
                "user_prompt": user_prompt,
                "assistant_content": assistant_content,
                "provider": provider,
                "model": model,
            }
        )


def _canned_events() -> list[StreamEvent]:
    return [
        StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.START.value),
        StreamEvent(
            category=EventCategory.GENERATION,
            type=CoreEventType.TOKEN.value,
            content="Hello",
        ),
        StreamEvent(
            category=EventCategory.GENERATION,
            type=CoreEventType.TOKEN.value,
            content=" world",
        ),
        StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.COMPLETE.value),
    ]


@pytest.fixture
def fakes() -> Iterator[tuple[_FakeStreamingService, _FakeConversationService]]:
    streaming_service = _FakeStreamingService(_canned_events())
    conversation_service = _FakeConversationService()

    app.dependency_overrides[get_streaming_service] = lambda: streaming_service
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service

    yield streaming_service, conversation_service

    del app.dependency_overrides[get_streaming_service]
    del app.dependency_overrides[get_conversation_service]


def test_stream_chat_requires_authentication(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService],
) -> None:
    response = client.post(
        "/api/v1/chat/stream",
        json={"user_prompt": "hi"},
    )

    assert response.status_code == 401


def test_stream_chat_returns_sse_frames_in_order(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService],
) -> None:
    streaming_service, _ = fakes

    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.post(
            "/api/v1/chat/stream",
            json={"user_prompt": "hi there"},
        )
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    assert "event: start" in body
    assert "event: token" in body
    assert "event: complete" in body
    assert body.index("event: start") < body.index("event: complete")

    assert streaming_service.received_requests[-1].user_prompt == "hi there"


def test_stream_chat_persists_the_assembled_turn_on_complete(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService],
) -> None:
    _, conversation_service = fakes

    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.post(
            "/api/v1/chat/stream",
            json={"user_prompt": "hi there"},
        )
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 200
    assert len(conversation_service.appended_turns) == 1

    turn = conversation_service.appended_turns[0]
    assert turn["conversation_id"] == _CONVERSATION_ID
    assert turn["user_prompt"] == "hi there"
    assert turn["assistant_content"] == "Hello world"
