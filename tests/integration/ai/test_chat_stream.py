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
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from app.ai.memory.enums import MemoryScopeType
from app.ai.memory.models import ExtractedMemory, MemoryContext
from app.ai.memory.session.state_updater import SessionStateDistillation
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationAttachment,
    GenerationRequest,
    StreamEventType,
)
from app.auth.dependencies import get_current_user
from app.dependencies.generation import (
    get_chat_attachment_repository,
    get_chat_attachment_service,
    get_conversation_service,
    get_generation_service,
    get_streaming_service,
)
from app.dependencies.memory import (
    get_memory_extraction_service,
    get_memory_service,
    get_session_state_updater_service,
)
from app.dependencies.project import get_project_authorization_service
from app.dependencies.rate_limiting import get_rate_limiter
from app.dependencies.research import (
    get_paper_query_extraction_service,
    get_paper_search_service,
    get_web_search_necessity_service,
    get_web_search_service,
)
from app.exceptions.base import NotFoundException
from app.infrastructure.rate_limiting import RateLimitResult
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

    async def get_or_create(self, *, conversation_id, owner_id, project_id=None) -> Conversation:
        return Conversation(
            id=_CONVERSATION_ID,
            owner_id=owner_id,
            project_id=project_id,
            title="Chat about LoRA",
            created_at=self.created_at,
            updated_at=self.created_at,
        )

    async def list_for_owner(
        self, *, owner_id, project_id=None, limit: int = 50
    ) -> list[Conversation]:
        return [
            await self.get_or_create(
                conversation_id=_CONVERSATION_ID, owner_id=owner_id, project_id=project_id
            )
        ]

    async def list_page_for_owner(
        self, *, owner_id, before_conversation_id=None, limit: int = 50, project_id=None
    ):
        return SimpleNamespace(
            conversations=await self.list_for_owner(
                owner_id=owner_id, project_id=project_id, limit=limit
            ),
            next_cursor=None,
        )

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

    async def list_messages_page(self, *, conversation_id, before_message_id=None, limit: int = 50):
        return SimpleNamespace(
            messages=await self.list_messages(conversation_id=conversation_id, limit=limit),
            next_cursor=None,
        )

    async def get_first_user_prompt(self, *, conversation_id) -> str:
        return "What are applications of RAG?"

    async def load_history(self, *, conversation_id, limit: int = 50) -> list:
        return []

    async def compact_history_if_needed(
        self, *, conversation, recent_message_limit: int, summary_max_characters: int
    ) -> None:
        return None

    async def load_prompt_history(self, *, conversation, recent_message_limit: int):
        return SimpleNamespace(summary=None, messages=[])

    async def append_turn(
        self,
        *,
        conversation_id,
        user_prompt,
        assistant_content,
        provider=None,
        model=None,
        attachment_ids=None,
    ) -> None:
        self.appended_turns.append(
            {
                "conversation_id": conversation_id,
                "user_prompt": user_prompt,
                "assistant_content": assistant_content,
                "provider": provider,
                "model": model,
                "attachment_ids": attachment_ids,
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
    """Stands in for MemoryService -- records remember()/get_context() calls,
    returns an empty MemoryContext so injection is a no-op by default."""

    def __init__(self) -> None:
        self.remembered: list[dict] = []
        self.context_calls: list[dict] = []

    async def get_context(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        semantic_query: str | None = None,
        top_k: int = 5,
        **kwargs: object,
    ) -> MemoryContext:
        self.context_calls.append(
            {"owner_id": owner_id, "session_id": session_id, **kwargs},
        )
        return MemoryContext()

    async def remember(self, **kwargs) -> None:
        self.remembered.append(kwargs)

    async def get_latest_session_state(self, **kwargs) -> None:
        return None

    async def update_memory(self, **kwargs) -> None:
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


class _FakeProjectAuthorization:
    """Stands in for ProjectAuthorizationService -- always authorizes,
    so tests can pass a `project_id` without seeding a real Project row."""

    def __init__(self) -> None:
        self.authorized_project_ids: list[uuid.UUID] = []

    async def authorize_project_access(self, *, user_id: UUID, project_id: UUID) -> None:
        self.authorized_project_ids.append(project_id)

    async def authorize_for_new_conversation(
        self, *, conversation_id: UUID | None, project_id: UUID | None, user_id: UUID
    ) -> None:
        if conversation_id is not None or project_id is None:
            return
        await self.authorize_project_access(user_id=user_id, project_id=project_id)


class _FakeChatAttachmentService:
    """Stands in for ChatAttachmentService -- no attachment id resolves
    unless explicitly registered via `known`, so tests don't depend on a
    real `chat_attachments` row/table existing. Mirrors the real
    service's `resolve_for_generation` contract: raises `NotFoundException`
    generically for any id that isn't owned/known, never partially
    resolves a batch."""

    def __init__(self) -> None:
        self.known: dict[uuid.UUID, GenerationAttachment] = {}

    async def resolve_for_generation(
        self,
        attachment_ids: list[uuid.UUID],
        *,
        owner_id: UUID,
    ) -> list[GenerationAttachment]:
        if not attachment_ids:
            return []

        resolved = [self.known[aid] for aid in attachment_ids if aid in self.known]

        if len(resolved) != len(set(attachment_ids)):
            raise NotFoundException("One or more attachments were not found.")

        return resolved

    async def generate_view_url(self, attachment) -> str:
        return "https://s3.example.com/fake-signed-url"


class _FakeChatAttachmentRepository:
    """Stands in for ChatAttachmentRepository -- no message has
    attachments unless a test registers them directly."""

    async def list_by_message_ids(self, message_ids: list[uuid.UUID]) -> list:
        return []


class _FakeRateLimiter:
    """Stands in for ValkeyRateLimiter -- allows by default; tests flip `allowed`."""

    def __init__(self, *, allowed: bool = True, retry_after_seconds: int = 0) -> None:
        self.allowed = allowed
        self.retry_after_seconds = retry_after_seconds
        self.calls: list[dict] = []

    async def check(self, *, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        self.calls.append({"key": key, "limit": limit, "window_seconds": window_seconds})
        return RateLimitResult(
            allowed=self.allowed,
            retry_after_seconds=self.retry_after_seconds,
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
def fakes() -> Iterator[
    tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService]
]:
    streaming_service = _FakeStreamingService(_canned_events())
    conversation_service = _FakeConversationService()
    memory_service = _FakeMemoryService()
    memory_extraction_service = _FakeMemoryExtractionService()
    # `distill()` returning None makes `distill_and_upsert_session_state()`
    # a clean no-op (matches "no schema-valid output" failing open) --
    # this avoids the real, network/API-key-requiring composition function.
    session_state_updater = SimpleNamespace(distill=AsyncMock(return_value=None))
    generation_service = _FakeGenerationService()
    chat_attachment_service = _FakeChatAttachmentService()
    chat_attachment_repository = _FakeChatAttachmentRepository()
    rate_limiter = _FakeRateLimiter()
    # `web_search_enabled`/`paper_search_enabled` default to False on every
    # payload below, so `run_chat_web_search`/`run_chat_paper_search` always
    # short-circuit before touching any of these -- they only need to
    # exist, not do anything, so the real (network/API-key-requiring)
    # composition functions never run in tests.
    web_search = SimpleNamespace(available=False)
    web_search_necessity = SimpleNamespace()
    paper_search = SimpleNamespace(available=False)
    paper_query_extraction = SimpleNamespace()

    app.dependency_overrides[get_streaming_service] = lambda: streaming_service
    app.dependency_overrides[get_generation_service] = lambda: generation_service
    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_chat_attachment_service] = lambda: chat_attachment_service
    app.dependency_overrides[get_chat_attachment_repository] = lambda: chat_attachment_repository
    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_memory_extraction_service] = lambda: memory_extraction_service
    app.dependency_overrides[get_session_state_updater_service] = lambda: session_state_updater
    app.dependency_overrides[get_rate_limiter] = lambda: rate_limiter
    app.dependency_overrides[get_web_search_service] = lambda: web_search
    app.dependency_overrides[get_web_search_necessity_service] = lambda: web_search_necessity
    app.dependency_overrides[get_paper_search_service] = lambda: paper_search
    app.dependency_overrides[get_paper_query_extraction_service] = lambda: paper_query_extraction

    yield streaming_service, conversation_service, generation_service

    del app.dependency_overrides[get_streaming_service]
    del app.dependency_overrides[get_generation_service]
    del app.dependency_overrides[get_conversation_service]
    del app.dependency_overrides[get_chat_attachment_service]
    del app.dependency_overrides[get_chat_attachment_repository]
    del app.dependency_overrides[get_memory_service]
    del app.dependency_overrides[get_memory_extraction_service]
    del app.dependency_overrides[get_session_state_updater_service]
    del app.dependency_overrides[get_rate_limiter]
    del app.dependency_overrides[get_web_search_service]
    del app.dependency_overrides[get_web_search_necessity_service]
    del app.dependency_overrides[get_paper_search_service]
    del app.dependency_overrides[get_paper_query_extraction_service]


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


def test_stream_chat_rejects_more_than_five_attachment_ids(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    """Wave 4 chat attachments cap at 5/turn (docs/PRIORITIZED_ROADMAP.md)
    -- enforced by `ChatStreamRequest.attachment_ids`'s `max_length=5`, so
    a 6th id must be a 422 before any conversation/generation work starts."""

    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "user_prompt": "hi there",
                "attachment_ids": [str(uuid.uuid4()) for _ in range(6)],
            },
        )
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 422


def test_stream_chat_rejects_an_attachment_id_that_does_not_resolve(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    """An attachment id that was never uploaded (or belongs to another
    owner) must fail closed -- `ChatAttachmentService.resolve_for_generation`
    raises generically rather than silently dropping it."""

    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "user_prompt": "hi there",
                "attachment_ids": [str(uuid.uuid4())],
            },
        )
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 404


def test_stream_chat_with_project_id_resolves_project_memory_scope(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    """The M5 memory-scope activation: a new conversation created with
    `project_id` must resolve `MemoryScopeType.PROJECT` (not the default
    PERSONAL) on every memory call the turn makes -- both the pre-generation
    retrieval and the post-generation session-state write."""

    project_id = uuid.uuid4()
    memory_service = _FakeMemoryService()
    project_authorization = _FakeProjectAuthorization()
    # Override the shared fixture's no-op `distill` so the session-state
    # write branch actually runs `remember()` (a real distillation with no
    # `previous` state takes the `else: remember(...)` path in
    # `distill_and_upsert_session_state`), letting this test observe scope
    # on the write side too, not just retrieval.
    session_state_updater = SimpleNamespace(
        distill=AsyncMock(
            return_value=SessionStateDistillation(has_topic=True, content="Discussing LoRA")
        )
    )

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_project_authorization_service] = lambda: project_authorization
    app.dependency_overrides[get_session_state_updater_service] = lambda: session_state_updater

    try:
        response = client.post(
            "/api/v1/chat/stream",
            json={"user_prompt": "hi there", "project_id": str(project_id)},
        )
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_project_authorization_service]
        # `get_memory_service`/`get_session_state_updater_service` are left
        # as-is here (not deleted) -- the `fakes` fixture set them first and
        # owns tearing them down; deleting them here too would make its own
        # `del` raise `KeyError` on an already-removed key.

    assert response.status_code == 200
    assert project_authorization.authorized_project_ids == [project_id]

    assert memory_service.context_calls
    assert memory_service.context_calls[-1]["scope_type"] == MemoryScopeType.PROJECT
    assert memory_service.context_calls[-1]["project_id"] == project_id

    assert memory_service.remembered
    assert memory_service.remembered[-1]["scope_type"] == MemoryScopeType.PROJECT
    assert memory_service.remembered[-1]["project_id"] == project_id


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


def test_stream_chat_uses_first_question_when_title_model_fails(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    _, conversation_service, generation_service = fakes
    generation_service.generate = AsyncMock(side_effect=RuntimeError("model unavailable"))  # type: ignore[method-assign]
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.post("/api/v1/chat/stream", json={"user_prompt": "first turn"})
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 200
    assert conversation_service.titles == ["What are applications of RAG"]


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
    assert replayed.json()["next_cursor"] is None


def test_stream_chat_returns_429_when_rate_limited(
    client: TestClient,
    fakes: tuple[_FakeStreamingService, _FakeConversationService, _FakeGenerationService],
) -> None:
    streaming_service, _, _ = fakes
    limited = _FakeRateLimiter(allowed=False, retry_after_seconds=42)
    app.dependency_overrides[get_current_user] = _fake_user
    # Overwrites (not adds) the `fakes` fixture's own override -- that
    # fixture's teardown still owns removing this key afterward.
    app.dependency_overrides[get_rate_limiter] = lambda: limited

    try:
        response = client.post("/api/v1/chat/stream", json={"user_prompt": "hi there"})
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    # The limited request never reached generation -- no cost incurred.
    assert streaming_service.received_requests == []
