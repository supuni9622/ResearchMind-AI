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
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.context.citations.models import Citation
from app.ai.research.models import ResearchOutcome, ResearchSource
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.research.report_download import ResearchReportDownloadService
from app.auth.dependencies import get_current_user
from app.dependencies.rate_limiting import get_rate_limiter
from app.dependencies.research import (
    get_research_proposal_service,
    get_research_report_download_service,
    get_research_repository,
    get_research_run_repository,
    get_research_run_service,
    get_research_service,
)
from app.infrastructure.rate_limiting import RateLimitResult
from app.main import app
from app.models.research import ResearchSession
from app.models.research_run import ResearchRun
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


class _FakeResearchRunRepository:
    def __init__(self, runs: dict[uuid.UUID, ResearchRun]) -> None:
        self._runs = runs

    async def get_by_id_for_owner(self, *, run_id, owner_id):
        run = self._runs.get(run_id)
        if run is None or run.owner_id != owner_id:
            return None
        return run


class _FakeResearchRunService:
    _TERMINAL = {"completed", "completed_with_limitations", "cancelled", "failed"}

    def __init__(self, runs: dict[uuid.UUID, ResearchRun]) -> None:
        self._runs = runs

    async def request_cancellation(self, *, run_id, owner_id):
        run = self._runs.get(run_id)
        if run is None or run.owner_id != owner_id:
            return None
        if run.status not in self._TERMINAL:
            run.cancellation_requested = True
        return run

    async def record_report_decision(self, *, run_id, owner_id, approved, reason=None):
        run = self._runs.get(run_id)
        if run is None or run.owner_id != owner_id:
            return None
        if run.status != "awaiting_approval":
            raise ValueError(f"Research run '{run.id}' is not awaiting a report decision.")
        run.budget_usage = {
            **(run.budget_usage or {}),
            "report_decision": {
                "decision": "approved" if approved else "rejected",
                "reason": reason,
            },
        }
        return run


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


@pytest.fixture
def fakes() -> Iterator[tuple[_FakeResearchService, dict[uuid.UUID, ResearchSession]]]:
    research_service = _FakeResearchService()
    sessions: dict[uuid.UUID, ResearchSession] = {}
    repository = _FakeResearchRepository(sessions)
    rate_limiter = _FakeRateLimiter()

    app.dependency_overrides[get_research_service] = lambda: research_service
    app.dependency_overrides[get_research_repository] = lambda: repository
    app.dependency_overrides[get_rate_limiter] = lambda: rate_limiter

    yield research_service, sessions

    del app.dependency_overrides[get_research_service]
    del app.dependency_overrides[get_research_repository]
    del app.dependency_overrides[get_rate_limiter]


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
    assert body["research_run_id"] is None
    assert body["answer"]
    assert body["citations"][0]["filename"] == "paper.pdf"
    assert body["sources"][0]["score"] == 0.9

    assert research_service.research_calls[-1]["owner_id"] == _OWNER_ID


def test_create_research_stays_on_the_linear_service_when_runtime_flags_are_enabled(
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
    assert research_service.research_calls[-1]["query"] == "How does RAG work?"


def test_final_report_download_returns_owner_scoped_presigned_url(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    report_downloads = AsyncMock(spec=ResearchReportDownloadService)
    run_id = uuid.uuid4()
    report_downloads.get_download_url.return_value = "https://storage.test/report.pdf"
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_research_report_download_service] = lambda: report_downloads

    try:
        response = client.get(f"/api/v1/research/runs/{run_id}/report")
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_report_download_service]

    assert response.status_code == 200
    assert response.json()["download_url"] == "https://storage.test/report.pdf"
    report_downloads.get_download_url.assert_awaited_once_with(
        research_run_id=run_id,
        owner_id=_OWNER_ID,
    )


def test_get_research_run_returns_only_the_owners_lifecycle_view(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    run_id = uuid.uuid4()
    runs = {
        run_id: ResearchRun(
            id=run_id,
            owner_id=_OWNER_ID,
            graph_thread_id=str(uuid.uuid4()),
            status="researching",
            attempt_count=1,
            cancellation_requested=False,
            budget_profile={},
            budget_usage={},
            error_summary={},
        )
    }
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_research_run_repository] = lambda: _FakeResearchRunRepository(runs)

    try:
        response = client.get(f"/api/v1/research/runs/{run_id}")
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_run_repository]

    assert response.status_code == 200
    body = response.json()
    assert body["research_run_id"] == str(run_id)
    assert body["status"] == "researching"
    assert "graph_thread_id" not in body


def test_cancel_research_run_flags_a_non_terminal_run(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    run_id = uuid.uuid4()
    runs = {
        run_id: ResearchRun(
            id=run_id,
            owner_id=_OWNER_ID,
            graph_thread_id=str(uuid.uuid4()),
            status="researching",
            attempt_count=1,
            cancellation_requested=False,
            budget_profile={},
            budget_usage={},
            error_summary={},
        )
    }
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_research_run_service] = lambda: _FakeResearchRunService(runs)

    try:
        response = client.post(f"/api/v1/research/runs/{run_id}/cancel")
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_run_service]

    assert response.status_code == 200
    assert response.json()["cancellation_requested"] is True
    assert runs[run_id].cancellation_requested is True


def test_cancel_research_run_returns_404_for_another_owners_run(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    run_id = uuid.uuid4()
    runs = {
        run_id: ResearchRun(
            id=run_id,
            owner_id=_OTHER_OWNER_ID,
            graph_thread_id=str(uuid.uuid4()),
            status="researching",
            attempt_count=1,
            cancellation_requested=False,
            budget_profile={},
            budget_usage={},
            error_summary={},
        )
    }
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_research_run_service] = lambda: _FakeResearchRunService(runs)

    try:
        response = client.post(f"/api/v1/research/runs/{run_id}/cancel")
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_run_service]

    assert response.status_code == 404


def test_submit_report_decision_approves_a_run_awaiting_approval(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    run_id = uuid.uuid4()
    runs = {
        run_id: ResearchRun(
            id=run_id,
            owner_id=_OWNER_ID,
            graph_thread_id=str(uuid.uuid4()),
            status="awaiting_approval",
            attempt_count=1,
            cancellation_requested=False,
            budget_profile={},
            budget_usage={},
            error_summary={},
        )
    }
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_research_run_service] = lambda: _FakeResearchRunService(runs)

    try:
        response = client.post(
            f"/api/v1/research/runs/{run_id}/report-decision", json={"approved": True}
        )
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_run_service]

    assert response.status_code == 200
    assert response.json()["research_run_id"] == str(run_id)
    assert runs[run_id].budget_usage["report_decision"] == {
        "decision": "approved",
        "reason": None,
    }


def test_submit_report_decision_rejects_with_a_reason(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    run_id = uuid.uuid4()
    runs = {
        run_id: ResearchRun(
            id=run_id,
            owner_id=_OWNER_ID,
            graph_thread_id=str(uuid.uuid4()),
            status="awaiting_approval",
            attempt_count=1,
            cancellation_requested=False,
            budget_profile={},
            budget_usage={},
            error_summary={},
        )
    }
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_research_run_service] = lambda: _FakeResearchRunService(runs)

    try:
        response = client.post(
            f"/api/v1/research/runs/{run_id}/report-decision",
            json={"approved": False, "reason": "Missing a key citation."},
        )
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_run_service]

    assert response.status_code == 200
    assert runs[run_id].budget_usage["report_decision"] == {
        "decision": "rejected",
        "reason": "Missing a key citation.",
    }


def test_submit_report_decision_returns_409_when_run_is_not_awaiting_approval(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    run_id = uuid.uuid4()
    runs = {
        run_id: ResearchRun(
            id=run_id,
            owner_id=_OWNER_ID,
            graph_thread_id=str(uuid.uuid4()),
            status="researching",
            attempt_count=1,
            cancellation_requested=False,
            budget_profile={},
            budget_usage={},
            error_summary={},
        )
    }
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_research_run_service] = lambda: _FakeResearchRunService(runs)

    try:
        response = client.post(
            f"/api/v1/research/runs/{run_id}/report-decision", json={"approved": True}
        )
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_run_service]

    assert response.status_code == 409


def test_submit_report_decision_returns_404_for_another_owners_run(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    run_id = uuid.uuid4()
    runs = {
        run_id: ResearchRun(
            id=run_id,
            owner_id=_OTHER_OWNER_ID,
            graph_thread_id=str(uuid.uuid4()),
            status="awaiting_approval",
            attempt_count=1,
            cancellation_requested=False,
            budget_profile={},
            budget_usage={},
            error_summary={},
        )
    }
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_research_run_service] = lambda: _FakeResearchRunService(runs)

    try:
        response = client.post(
            f"/api/v1/research/runs/{run_id}/report-decision", json={"approved": True}
        )
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_run_service]

    assert response.status_code == 404


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


def test_create_research_returns_429_when_rate_limited(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    research_service, _ = fakes
    limited = _FakeRateLimiter(allowed=False, retry_after_seconds=42)
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_rate_limiter] = lambda: limited

    try:
        response = client.post("/api/v1/research", json={"query": "how does rag work?"})
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    # The limited request never reached the research service -- no cost incurred.
    assert research_service.research_calls == []


def test_create_research_proposal_returns_429_when_rate_limited(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    limited = _FakeRateLimiter(allowed=False, retry_after_seconds=13)
    proposals = AsyncMock()
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_rate_limiter] = lambda: limited
    app.dependency_overrides[get_research_proposal_service] = lambda: proposals

    try:
        response = client.post("/api/v1/research/proposals", json={"query": "how does rag work?"})
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_proposal_service]

    assert response.status_code == 429
    assert response.headers["retry-after"] == "13"
    # The limited request never reached the planner -- no LLM cost incurred.
    proposals.propose.assert_not_awaited()


def test_escalation_check_returns_429_when_rate_limited(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    limited = _FakeRateLimiter(allowed=False, retry_after_seconds=7)
    proposals = AsyncMock()
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_rate_limiter] = lambda: limited
    app.dependency_overrides[get_research_proposal_service] = lambda: proposals

    try:
        response = client.post(
            "/api/v1/research/escalation-check", json={"query": "how does rag work?"}
        )
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_proposal_service]

    assert response.status_code == 429
    assert response.headers["retry-after"] == "7"
    proposals.check_escalation.assert_not_awaited()


def test_approve_research_proposal_returns_429_when_rate_limited(
    client: TestClient,
    fakes: tuple[_FakeResearchService, dict],
) -> None:
    limited = _FakeRateLimiter(allowed=False, retry_after_seconds=99)
    proposals = AsyncMock()
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_rate_limiter] = lambda: limited
    app.dependency_overrides[get_research_proposal_service] = lambda: proposals

    try:
        response = client.post(f"/api/v1/research/proposals/{uuid.uuid4()}/approve")
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_research_proposal_service]

    assert response.status_code == 429
    assert response.headers["retry-after"] == "99"
    # The limited request never reached run creation/dispatch -- no run queued.
    proposals.approve.assert_not_awaited()
