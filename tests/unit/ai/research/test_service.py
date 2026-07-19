"""
Unit tests for ResearchService.

Covers:
- research(): scopes retrieval to the caller's owner_id, builds a
  GenerationRequest tagged runtime=RESEARCH/artifact_runtime=RESEARCH,
  executes through the injected GenerationRuntime, persists the session,
  and best-effort persists the Research Artifact
- Artifact persistence is skipped when no writer is wired, gated by the
  ArtifactPolicyService, and never raises on a storage failure
- citations_only(): retrieval + context building only, no generation, no
  persistence
- stream_research(): emits RESEARCH_STARTED/RETRIEVAL_STARTED/
  RETRIEVAL_COMPLETED before forwarding StreamingService's own events,
  and persists on COMPLETE
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.ai.research.service import ResearchService
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.generation.enums import GenerationProvider

from tests.unit.ai.research.factories import (
    make_context_result,
    make_generation_result,
    make_retrieval_result,
)


def _make_service(
    *,
    session: AsyncMock | None = None,
    retrieval_result=None,
    context_result=None,
    generation_result=None,
    stream_events: list[StreamEvent] | None = None,
    research_artifact_writer: AsyncMock | None = None,
    artifact_policy_service: MagicMock | None = None,
) -> tuple[ResearchService, dict]:
    session = session or AsyncMock()
    session.add = MagicMock()

    # `ResearchConversationService.load_history()` (conversation
    # threading) queries `session.execute(...).scalars().all()` for
    # prior turns -- without this, the bare `AsyncMock` session makes
    # `.scalars()` resolve to a coroutine (an `AsyncMock` child), not a
    # chainable result. Tests here don't exercise multi-turn history, so
    # "no prior turns" is the right default.
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result)

    retrieval_service = AsyncMock()
    retrieval_service.search_hybrid = AsyncMock(
        return_value=retrieval_result or make_retrieval_result(),
    )

    context_builder = AsyncMock()
    context_builder.build = AsyncMock(return_value=context_result or make_context_result())

    generation_runtime = AsyncMock()
    generation_runtime.execute = AsyncMock(
        return_value=generation_result or make_generation_result(),
    )

    async def _events() -> AsyncGenerator[StreamEvent, None]:
        for event in stream_events or []:
            yield event

    streaming_service = MagicMock()
    streaming_service.stream_generate = MagicMock(side_effect=lambda **kwargs: _events())

    service = ResearchService(
        session=session,
        retrieval_service=retrieval_service,
        context_builder=context_builder,
        generation_runtime=generation_runtime,
        streaming_service=streaming_service,
        research_artifact_writer=research_artifact_writer,
        artifact_policy_service=artifact_policy_service,
    )

    collaborators = {
        "session": session,
        "retrieval_service": retrieval_service,
        "context_builder": context_builder,
        "generation_runtime": generation_runtime,
        "streaming_service": streaming_service,
    }

    return service, collaborators


async def test_research_scopes_retrieval_to_owner_id() -> None:
    owner_id = uuid4()

    service, collaborators = _make_service()

    await service.research(
        query="How does RAG work?",
        top_k=10,
        filters={"owner_id": "someone-else", "language": "en"},
        owner_id=owner_id,
    )

    query = collaborators["retrieval_service"].search_hybrid.await_args.kwargs["query"]

    assert query.filters["owner_id"] == str(owner_id)
    assert query.filters["language"] == "en"


async def test_research_tags_the_generation_request_for_the_research_runtime() -> None:
    from app.ai.artifacts.enums import ArtifactRuntime
    from app.ai.runtime.generation.caching.enums import CacheRuntime
    from app.ai.runtime.generation.validation.runtime.enums import RuntimeType

    service, collaborators = _make_service()

    await service.research(
        query="How does RAG work?",
        top_k=10,
        filters={},
        owner_id=uuid4(),
    )

    request = collaborators["generation_runtime"].execute.await_args.args[0]

    assert request.runtime == RuntimeType.RESEARCH
    assert request.cache_runtime == CacheRuntime.RESEARCH
    assert request.artifact_runtime == ArtifactRuntime.RESEARCH


async def test_research_forwards_an_explicit_provider_override() -> None:
    service, collaborators = _make_service()

    await service.research(
        query="How does RAG work?",
        top_k=10,
        filters={},
        owner_id=uuid4(),
        provider=GenerationProvider.CLAUDE,
    )

    assert (
        collaborators["generation_runtime"].execute.await_args.kwargs["provider"]
        == GenerationProvider.CLAUDE
    )


async def test_research_persists_the_session() -> None:
    session = AsyncMock()

    service, _ = _make_service(session=session)

    outcome = await service.research(
        query="How does RAG work?",
        top_k=10,
        filters={},
        owner_id=uuid4(),
    )

    # add(): once for the (implicitly created) ResearchConversation, once
    # for the ResearchSession turn itself. commit(): those same two plus
    # one for the auto-title set from the first query.
    assert session.add.call_count == 2
    assert session.commit.await_count == 3

    persisted = session.add.call_args.args[0]
    assert persisted.query == "How does RAG work?"
    assert persisted.answer == outcome.answer


async def test_research_writes_the_artifact_when_a_writer_is_wired() -> None:
    writer = AsyncMock()

    service, _ = _make_service(research_artifact_writer=writer)

    await service.research(query="q", top_k=10, filters={}, owner_id=uuid4())

    writer.write.assert_awaited_once()


async def test_research_skips_the_artifact_when_no_writer_is_wired() -> None:
    service, _ = _make_service(research_artifact_writer=None)

    # Should not raise even though no writer is configured.
    await service.research(query="q", top_k=10, filters={}, owner_id=uuid4())


async def test_research_skips_the_artifact_when_the_policy_says_never() -> None:
    writer = AsyncMock()
    policy = MagicMock()
    policy.should_persist = MagicMock(return_value=False)

    service, _ = _make_service(
        research_artifact_writer=writer,
        artifact_policy_service=policy,
    )

    await service.research(query="q", top_k=10, filters={}, owner_id=uuid4())

    writer.write.assert_not_awaited()


async def test_research_swallows_an_artifact_write_failure() -> None:
    writer = AsyncMock()
    writer.write = AsyncMock(side_effect=RuntimeError("s3 is down"))

    service, _ = _make_service(research_artifact_writer=writer)

    # Must not raise -- artifact persistence is best-effort.
    outcome = await service.research(query="q", top_k=10, filters={}, owner_id=uuid4())

    assert outcome.answer


async def test_citations_only_never_calls_generation_or_persists() -> None:
    service, collaborators = _make_service()

    citations = await service.citations_only(
        query="How does RAG work?",
        top_k=10,
        filters={},
        owner_id=uuid4(),
    )

    assert citations == collaborators["context_builder"].build.return_value.prompt_context.citations

    collaborators["generation_runtime"].execute.assert_not_awaited()
    collaborators["session"].commit.assert_not_awaited()


async def test_stream_research_emits_research_events_before_generation_events() -> None:
    generation_events = [
        StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.START.value),
        StreamEvent(
            category=EventCategory.GENERATION,
            type=CoreEventType.TOKEN.value,
            content="RAG ",
        ),
        StreamEvent(
            category=EventCategory.GENERATION,
            type=CoreEventType.TOKEN.value,
            content="works.",
        ),
        StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.COMPLETE.value),
    ]

    service, collaborators = _make_service(stream_events=generation_events)

    events = [
        event
        async for event in service.stream_research(
            query="How does RAG work?",
            top_k=10,
            filters={},
            owner_id=uuid4(),
        )
    ]

    types = [event.type for event in events]

    assert types == [
        ResearchEventType.RESEARCH_STARTED.value,
        ResearchEventType.RETRIEVAL_STARTED.value,
        ResearchEventType.RETRIEVAL_COMPLETED.value,
        CoreEventType.START.value,
        CoreEventType.TOKEN.value,
        CoreEventType.TOKEN.value,
        CoreEventType.COMPLETE.value,
    ]

    # commit(): once for the (implicitly created) ResearchConversation,
    # once for the auto-title set from the first query, once for the
    # ResearchSession turn itself.
    assert collaborators["session"].commit.await_count == 3

    persisted = collaborators["session"].add.call_args.args[0]
    assert persisted.answer == "RAG works."
