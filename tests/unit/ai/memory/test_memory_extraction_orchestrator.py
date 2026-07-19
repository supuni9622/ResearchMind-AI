from unittest.mock import AsyncMock
from uuid import uuid4

from app.ai.memory.enums import MemoryType
from app.ai.memory.extraction.orchestrator import MemoryExtractionOrchestrator
from app.ai.memory.models import ExtractedMemory
from app.ai.memory.policy.interest_promotion import RepeatedInterestPromotionService
from app.ai.memory.policy.models import MemoryTurnEvent


def _event(message: str = "Remember that I prefer concise answers") -> MemoryTurnEvent:
    identifier = uuid4()
    return MemoryTurnEvent(
        owner_id=identifier,
        session_id=identifier,
        conversation_id=identifier,
        runtime="chat",
        user_message=message,
        assistant_message="Noted.",
        turn_id="message-id",
    )


async def test_skipped_turn_never_calls_extractor() -> None:
    extractor = AsyncMock()
    outcome = await MemoryExtractionOrchestrator(AsyncMock(), extractor).process_turn(
        _event("Thanks")
    )
    assert outcome.skipped_count == 1
    extractor.extract.assert_not_awaited()


async def test_eligible_turn_records_created_outcome() -> None:
    memory = AsyncMock()
    memory.remember_extracted = AsyncMock(return_value=(object(), "created"))
    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        return_value=[
            ExtractedMemory(
                content="User prefers concise answers",
                type=MemoryType.USER,
                importance=0.8,
            )
        ]
    )
    outcome = await MemoryExtractionOrchestrator(memory, extractor).process_turn(_event())
    assert outcome.created_count == 1
    assert outcome.extracted_count == 1


async def test_duplicate_idempotency_key_does_not_call_extractor() -> None:
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=False)
    extractor = AsyncMock()
    outcome = await MemoryExtractionOrchestrator(AsyncMock(), extractor, redis).process_turn(
        _event()
    )
    assert outcome.skipped_count == 1
    extractor.extract.assert_not_awaited()


async def test_repeated_topic_promotion_uses_llm_once_eligible() -> None:
    memory = AsyncMock()
    memory.remember_extracted = AsyncMock(return_value=(object(), "created"))
    extractor = AsyncMock()
    extractor.extract = AsyncMock(return_value=[])
    promotion = AsyncMock(spec=RepeatedInterestPromotionService)
    promotion.promoted_topics = AsyncMock(return_value=["rag"])

    outcome = await MemoryExtractionOrchestrator(
        memory,
        extractor,
        interest_promotion=promotion,
    ).process_turn(_event("What is RAG?"))

    assert outcome.decision.reasons == ["repeated_topic_engagement"]
    extractor.extract.assert_awaited_once()
    assert extractor.extract.await_args.kwargs["interest_topics"] == ["rag"]
