"""
Integration tests for POST /api/v1/chat/stream.

Covers:
- Requires authentication (401 without a bearer token)
- A live stream is returned as `text/event-stream` SSE frames in order
- The completed turn is persisted (via ConversationService.append_turn)
  with the assembled content once the stream reaches COMPLETE

StreamingService, ConversationService, MemoryService and
MemoryExtractionService are all faked (like _FakeRetrievalService in
test_retrieval_filters.py) rather than run against a live LLM provider,
embedding provider, or a real Postgres session shared across the
TestClient's independent event loop.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from app.ai.memory.models import ExtractedMemory, MemoryContext
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.auth.dependencies import get_current_user
from app.dependencies.generation import (
    get_conversation_service,
    get_generation_service,
    get_streaming_service,
)
from app.dependencies.memory import get_memory_extraction_service, get_memory_service
from app.main import app
from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole
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
        self.titles: list[str] = []
        self.title_claimed = False
        self.created_at = datetime.now(UTC)

    async def get_or_create(self, *, conversation_id, owner_id) -> Conversation:
        return Conversation(
            id=_CONVERSATION_ID,
            owner_id=owner_id,
            title="Chat about LoRA",
            created_at=self.created_at,
            updated_at=self.created_at,
        )

    async def list_for_owner(self, *, owner_id, limit: int = 50) -> list[Conversation]:
        return [await self.get_or_create(conversation_id=_CONVERSATION_ID, owner_id=owner_id)]

    async def list_messages(self, *, conversation_id, limit: int = 50) -> list[Message]:
        return [
            Message(
                id=uuid.uuid4(),
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content="Explain LoRA.",
                created_at=self.created_at,
                updated_at=self.created_at,
            ),
            Message(
                id=uuid.uuid4(),
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content="LoRA is a parameter-efficient fine-tuning method.",
                provider="groq",
                created_at=self.created_at,
                updated_at=self.created_at,
            ),
        ]

    async def get_first_user_prompt(self, *, conversation_id) -> str:
        return "What are applications of RAG?"

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

    async def claim_title_generation(self, *, conversation_id):
        if self.title_claimed:
            return None
        self.title_claimed = True
        return uuid.uuid4()

    async def complete_title_generation(self, *, conversation_id, token, title: str) -> bool:
        self.titles.append(title)
        return True

    async def release_title_generation(self, *, conversation_id, token) -> None:
        self.title_claimed = False


class _FakeGenerationService:
    def __init__(self) -> None:
        self.requests: list[GenerationRequest] = []

    async def generate(self, *, request: GenerationRequest, provider: GenerationProvider):
        assert provider == GenerationProvider.GROQ
        self.requests.append(request)
        return SimpleNamespace(content="LoRA and QLoRA Comparison")


class _FakeMemoryService:
    """Stands in for MemoryService -- records remember() calls, returns
    an empty MemoryContext so injection is a no-op by default."""

    def __init__(self) -> None:
        self.remembered: list[dict] = []

    async def get_context(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        semantic_query: str | None = None,
        top_k: int = 5,
    ) -> MemoryContext:
        return MemoryContext()

    async def remember(self, **kwargs) -> None:
        self.remembered.append(kwargs)


class _FakeMemoryExtractionService:
    """Stands in for MemoryExtractionService -- proposes no memories."""

    async def extract(
        self,
        *,
        user_message: str,
        assistant_message: str,
        **_: object,
    ) -> list[ExtractedMemory]:
        return []


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
def fakes() -> Iterator[
    tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService]
]:
    streaming_service = _FakeStreamingService(_canned_events())
    conversation_service = _FakeConversationService()
    memory_service = _FakeMemoryService()
    memory_extraction_service = _FakeMemoryExtractionService()
    generation_service = _FakeGenerationService()

    app.dependency_overrides[get_streaming_service] = lambda: streaming_service
    app.dependency_overrides[get_generation_service] = lambda: generation_service
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_memory_extraction_service] = lambda: memory_extraction_service

    yield streaming_service, conversation_service, generation_service

    del app.dependency_overrides[get_streaming_service]
    del app.dependency_overrides[get_generation_service]
    del app.dependency_overrides[get_conversation_service]
    del app.dependency_overrides[get_memory_service]
    del app.dependency_overrides[get_memory_extraction_service]


def test_stream_chat_requires_authentication(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    response = client.post(
        "/api/v1/chat/stream",
        json={"user_prompt": "hi"},
    )

    assert response.status_code == 401


def test_stream_chat_returns_sse_frames_in_order(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    streaming_service, _, _ = fakes

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
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    _, conversation_service, generation_service = fakes

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
    assert conversation_service.titles == ["LoRA and QLoRA Comparison"]
    assert generation_service.requests[0].user_prompt == (
        "First user question: What are applications of RAG?"
    )


def test_stream_chat_generates_a_title_only_once_per_conversation(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    _, conversation_service, generation_service = fakes
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        client.post("/api/v1/chat/stream", json={"user_prompt": "first turn"})
        client.post(
            "/api/v1/chat/stream",
            json={"user_prompt": "a follow-up", "conversation_id": str(_CONVERSATION_ID)},
        )
    finally:
        del app.dependency_overrides[get_current_user]

    assert conversation_service.titles == ["LoRA and QLoRA Comparison"]
    assert len(generation_service.requests) == 1


def test_stream_chat_persists_a_provider_completed_event(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    streaming_service, conversation_service, _ = fakes
    streaming_service._events[-1] = StreamEvent(
        category=EventCategory.GENERATION,
        type=StreamEventType.COMPLETED.value,
    )
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.post("/api/v1/chat/stream", json={"user_prompt": "hi there"})
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 200
    assert len(conversation_service.appended_turns) == 1


def test_chat_history_is_available_over_authenticated_http(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        listed = client.get("/api/v1/chat/conversations")
        replayed = client.get(f"/api/v1/chat/conversations/{_CONVERSATION_ID}")
    finally:
        del app.dependency_overrides[get_current_user]

    assert listed.status_code == 200
    assert listed.json()["conversations"][0]["conversation_id"] == str(_CONVERSATION_ID)
    assert replayed.status_code == 200
    assert [message["role"] for message in replayed.json()["messages"]] == ["user", "assistant"]
