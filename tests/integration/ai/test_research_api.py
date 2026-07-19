"""
Integration tests for the Research API routes (research_api_prd.md).

Covers:
- All four routes require authentication (401 without a bearer token)
- POST /research returns a grounded answer with citations/sources
- POST /research/stream returns ordered SSE frames (research events
  before generation events)
- POST /research/citations returns citations without touching the
  generation collaborator
- GET /research/{id} 404s for a session that doesn't exist or belongs
  to another owner

ResearchService is faked at the route boundary (like
_FakeStreamingService/_FakeConversationService in test_chat_stream.py)
rather than run against live retrieval/context/generation platforms.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime

import pytest
from app.ai.knowledge.context.citations.models import Citation
from app.ai.research.models import ResearchOutcome, ResearchSource
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.events.research.models import ResearchEventType
from app.auth.dependencies import get_current_user
from app.dependencies.research import get_research_repository, get_research_service
from app.main import app
from app.models.research import ResearchSession
from app.models.user import User
from fastapi.testclient import TestClient

_OWNER_ID = uuid.uuid4()
_OTHER_OWNER_ID = uuid.uuid4()


def _fake_user() -> User:
    return User(
        id=_OWNER_ID,
        auth_provider="test",
        provider_user_id=str(_OWNER_ID),
        email="owner@example.com",
    )


def _outcome(*, query: str = "How does RAG work?") -> ResearchOutcome:
    document_id = uuid.uuid4()

    return ResearchOutcome(
        research_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        query=query,
        answer="RAG retrieves relevant context before generating an answer.",
        citations=[
            Citation(citation_id="c1", filename="paper.pdf", document_id=document_id),
        ],
        sources=[
            ResearchSource(
                document_id=document_id,
                filename="paper.pdf",
                chunk_id=uuid.uuid4(),
                score=0.9,
            ),
        ],
        duration_ms=42.0,
    )


class _FakeResearchService:
    """Stands in for ResearchService -- records the calls it received."""

    def __init__(self) -> None:
        self.research_calls: list[dict] = []
        self.citations_calls: list[dict] = []

    async def research(self, **kwargs) -> ResearchOutcome:
        self.research_calls.append(kwargs)
        return _outcome(query=kwargs["query"])

    async def stream_research(self, **kwargs) -> AsyncGenerator[StreamEvent, None]:
        yield StreamEvent(
            category=EventCategory.RESEARCH,
            type=ResearchEventType.RESEARCH_STARTED.value,
        )
        yield StreamEvent(
            category=EventCategory.RESEARCH,
            type=ResearchEventType.RETRIEVAL_STARTED.value,
        )
        yield StreamEvent(
            category=EventCategory.RESEARCH,
            type=ResearchEventType.RETRIEVAL_COMPLETED.value,
        )
        yield StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.START.value)
        yield StreamEvent(
            category=EventCategory.GENERATION,
            type=CoreEventType.TOKEN.value,
            content="RAG works.",
        )
        yield StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.COMPLETE.value)

    async def citations_only(self, **kwargs) -> list[Citation]:
        self.citations_calls.append(kwargs)
        return [Citation(citation_id="c1", filename="paper.pdf", document_id=uuid.uuid4())]


class _FakeResearchRepository:
    def __init__(self, sessions: dict[uuid.UUID, ResearchSession]) -> None:
        self._sessions = sessions

    async def get_by_id_for_owner(self, *, research_id, owner_id):
        session = self._sessions.get(research_id)

        if session is None or session.owner_id != owner_id:
            return None

        return session


@pytest.fixture
def fakes() -> Iterator[tuple[_FakeResearchService, dict[uuid.UUID, ResearchSession]]]:
    research_service = _FakeResearchService()
    sessions: dict[uuid.UUID, ResearchSession] = {}
    repository = _FakeResearchRepository(sessions)

    app.dependency_overrides[get_research_service] = lambda: research_service
    app.dependency_overrides[get_research_repository] = lambda: repository

    yield research_service, sessions

    del app.dependency_overrides[get_research_service]
    del app.dependency_overrides[get_research_repository]


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/research", {"query": "how does rag work?"}),
        ("post", "/research/stream", {"query": "how does rag work?"}),
        ("post", "/research/citations", {"query": "how does rag work?"}),
        ("get", "/research/" + str(uuid.uuid4()), None),
    ],
)
def test_research_routes_require_authentication(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
    method: str,
    path: str,
    payload: dict | None,
) -> None:
    if payload is None:
        response = getattr(client, method)(f"/api/v1{path}")
    else:
        response = getattr(client, method)(f"/api/v1{path}", json=payload)

    assert response.status_code == 401


def test_create_research_returns_a_grounded_answer(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    research_service, _ = fakes

    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.post(
            "/api/v1/research",
            json={"query": "How does RAG work?"},
        )
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 200

    body = response.json()
    assert body["query"] == "How does RAG work?"
    assert body["answer"]
    assert body["citations"][0]["filename"] == "paper.pdf"
    assert body["sources"][0]["score"] == 0.9

    assert research_service.research_calls[-1]["owner_id"] == _OWNER_ID


def test_stream_research_returns_ordered_sse_frames(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.post(
            "/api/v1/research/stream",
            json={"query": "How does RAG work?"},
        )
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    assert body.index(f"event: {ResearchEventType.RETRIEVAL_STARTED.value}") < body.index(
        f"event: {CoreEventType.START.value}"
    )
    assert body.index(f"event: {CoreEventType.START.value}") < body.index(
        f"event: {CoreEventType.COMPLETE.value}"
    )


def test_research_citations_returns_citations_only(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    research_service, _ = fakes

    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.post(
            "/api/v1/research/citations",
            json={"query": "How does RAG work?"},
        )
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 200
    assert response.json()["citations"][0]["filename"] == "paper.pdf"
    assert research_service.citations_calls[-1]["owner_id"] == _OWNER_ID


def test_get_research_returns_404_for_unknown_session(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.get(f"/api/v1/research/{uuid.uuid4()}")
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 404


def test_get_research_returns_404_for_another_owners_session(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    _, sessions = fakes

    research_id = uuid.uuid4()
    sessions[research_id] = ResearchSession(
        id=research_id,
        owner_id=_OTHER_OWNER_ID,
        query="q",
        answer="a",
        citations=[],
        sources=[],
        runtime_metadata={},
    )

    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.get(f"/api/v1/research/{research_id}")
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 404


def test_get_research_replays_the_owners_session(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    _, sessions = fakes

    research_id = uuid.uuid4()
    sessions[research_id] = ResearchSession(
        id=research_id,
        owner_id=_OWNER_ID,
        query="How does RAG work?",
        answer="RAG retrieves relevant context before generating an answer.",
        citations=[
            {"citation_id": "c1", "filename": "paper.pdf", "document_id": str(uuid.uuid4())}
        ],
        sources=[
            {
                "document_id": str(uuid.uuid4()),
                "filename": "paper.pdf",
                "chunk_id": str(uuid.uuid4()),
                "score": 0.9,
            }
        ],
        runtime_metadata={"provider": "groq"},
        created_at=datetime.now(UTC),
    )

    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.get(f"/api/v1/research/{research_id}")
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 200
    body = response.json()
    assert body["research_id"] == str(research_id)
    assert body["query"] == "How does RAG work?"
    assert body["citations"][0]["filename"] == "paper.pdf"
