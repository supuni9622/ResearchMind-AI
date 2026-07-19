from uuid import uuid4

from app.ai.memory.policy.models import MemoryExtractionAction, MemoryTurnEvent
from app.ai.memory.policy.service import MemoryExtractionPolicy


def _event(message: str, *, runtime: str = "chat") -> MemoryTurnEvent:
    identifier = uuid4()
    return MemoryTurnEvent(
        owner_id=identifier,
        session_id=identifier,
        runtime=runtime,
        user_message=message,
        assistant_message="A response.",
        turn_id="turn-1",
    )


def test_skips_trivial_and_generic_turns() -> None:
    policy = MemoryExtractionPolicy()

    assert policy.decide(_event("Thanks")).action == MemoryExtractionAction.SKIP
    assert policy.decide(_event("What is RAG?")).action == MemoryExtractionAction.SKIP


def test_extracts_explicit_memory_intent() -> None:
    decision = MemoryExtractionPolicy().decide(_event("Remember that I prefer concise answers"))

    assert decision.action == MemoryExtractionAction.EXTRACT_SYNC
    assert decision.explicit_request is True


def test_skips_internal_runtime() -> None:
    assert (
        MemoryExtractionPolicy()
        .decide(_event("We decided to use LangGraph", runtime="planner"))
        .action
        == MemoryExtractionAction.SKIP
    )


def test_extracts_durable_decisions() -> None:
    assert (
        MemoryExtractionPolicy()
        .decide(_event("We decided to use LangGraph for Research Runtime"))
        .action
        == MemoryExtractionAction.EXTRACT_ASYNC_READY
    )


def test_extracts_explicit_learning_interest() -> None:
    assert (
        MemoryExtractionPolicy()
        .decide(_event("I'm learning RAG to build a document assistant"))
        .action
        == MemoryExtractionAction.EXTRACT_ASYNC_READY
    )
