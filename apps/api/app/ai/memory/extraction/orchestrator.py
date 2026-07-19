"""Shared post-turn memory processing for Chat and Research."""

from __future__ import annotations

from contextlib import suppress
from time import perf_counter

import structlog
from redis.asyncio import Redis

from app.ai.memory.enums import MemoryType
from app.ai.memory.extraction.service import MemoryExtractionService
from app.ai.memory.observability.metrics import (
    EXTRACTION_EMPTY,
    EXTRACTION_EVALUATED,
    EXTRACTION_FAILED,
    EXTRACTION_LATENCY,
    EXTRACTION_REQUESTED,
    EXTRACTION_SKIPPED,
    EXTRACTION_SUCCEEDED,
)
from app.ai.memory.policy.interest_promotion import RepeatedInterestPromotionService
from app.ai.memory.policy.models import (
    MemoryExtractionAction,
    MemoryExtractionDecision,
    MemoryExtractionOutcome,
    MemoryTurnEvent,
)
from app.ai.memory.policy.service import MemoryExtractionPolicy
from app.ai.memory.services.memory_service import MemoryService
from app.core.settings import settings
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder

logger = structlog.get_logger()


class MemoryExtractionOrchestrator:
    def __init__(
        self,
        memory: MemoryService,
        extractor: MemoryExtractionService,
        idempotency_client: Redis | None = None,
        metrics: MetricsRecorder | None = None,
        interest_promotion: RepeatedInterestPromotionService | None = None,
    ) -> None:
        self._memory = memory
        self._extractor = extractor
        self._policy = MemoryExtractionPolicy()
        self._idempotency_client = idempotency_client
        self._metrics = metrics or NoOpMetricsRecorder()
        self._interest_promotion = interest_promotion or RepeatedInterestPromotionService(
            idempotency_client
        )

    async def process_turn(self, event: MemoryTurnEvent) -> MemoryExtractionOutcome:
        started = perf_counter()
        decision = self._policy.decide(event)
        if decision.action == MemoryExtractionAction.SKIP:
            promoted_topics = await self._interest_promotion.promoted_topics(
                owner_id=event.owner_id,
                session_id=event.session_id,
                user_message=event.user_message,
            )
            if promoted_topics:
                decision = MemoryExtractionDecision(
                    action=MemoryExtractionAction.EXTRACT_ASYNC_READY,
                    reasons=["repeated_topic_engagement"],
                    promotion_topics=promoted_topics,
                )
        self._metrics.increment(metric=EXTRACTION_EVALUATED)
        logger.info(
            "memory.extraction.policy_decided",
            owner_id=str(event.owner_id),
            session_id=str(event.session_id),
            conversation_id=str(event.conversation_id) if event.conversation_id else None,
            research_id=str(event.research_id) if event.research_id else None,
            runtime=event.runtime,
            policy_action=decision.action.value,
            policy_reasons=decision.reasons,
            policy_version=settings.memory_extraction_policy_version,
        )
        if decision.action == MemoryExtractionAction.SKIP:
            self._metrics.increment(metric=EXTRACTION_SKIPPED)
            logger.info(
                "memory.extraction.skipped",
                owner_id=str(event.owner_id),
                reasons=decision.reasons,
            )
            return MemoryExtractionOutcome(decision=decision, skipped_count=1)
        key = (
            f"memory:extraction:{event.owner_id}:{event.runtime}:"
            f"{event.turn_id}:{settings.memory_extraction_policy_version}"
        )
        claimed = False
        if self._idempotency_client is not None:
            try:
                claimed = bool(
                    await self._idempotency_client.set(
                        key,
                        "processing",
                        ex=settings.memory_extraction_idempotency_ttl_seconds,
                        nx=True,
                    )
                )
                if not claimed:
                    self._metrics.increment(metric=EXTRACTION_SKIPPED)
                    return MemoryExtractionOutcome(decision=decision, skipped_count=1)
            except Exception as exc:
                logger.warning(
                    "memory.extraction.idempotency_unavailable",
                    owner_id=str(event.owner_id),
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                claimed = False
        try:
            self._metrics.increment(metric=EXTRACTION_REQUESTED)
            logger.info(
                "memory.extraction.started",
                owner_id=str(event.owner_id),
                runtime=event.runtime,
            )
            extracted = await self._extractor.extract(
                user_message=event.user_message,
                assistant_message=event.assistant_message,
                owner_id=event.owner_id,
                conversation_id=event.conversation_id,
                interest_topics=decision.promotion_topics,
            )
            outcome = MemoryExtractionOutcome(
                decision=decision,
                extracted_count=len(extracted),
            )
            if not extracted:
                self._metrics.increment(metric=EXTRACTION_EMPTY)
            for item in extracted:
                if item.type not in {MemoryType.USER, MemoryType.RESEARCH}:
                    outcome.skipped_count += 1
                    logger.warning(
                        "memory.extraction.invalid_type",
                        owner_id=str(event.owner_id),
                        memory_type=item.type.value,
                    )
                    continue
                metadata = (
                    {"research_id": str(event.research_id)}
                    if item.type == MemoryType.RESEARCH and event.research_id
                    else None
                )
                record, status = await self._memory.remember_extracted(
                    owner_id=event.owner_id,
                    type=item.type,
                    content=item.content,
                    importance_score=item.importance,
                    metadata={
                        **(metadata or {}),
                        "source_turn_id": event.turn_id,
                        "policy_version": settings.memory_extraction_policy_version,
                    },
                )
                if status == "created":
                    outcome.created_count += 1
                elif status == "duplicate":
                    outcome.duplicate_count += 1
                    outcome.updated_count += 1
                else:
                    outcome.skipped_count += 1
            self._metrics.increment(metric=EXTRACTION_SUCCEEDED)
            logger.info(
                "memory.extraction.completed",
                owner_id=str(event.owner_id),
                runtime=event.runtime,
                extracted_count=outcome.extracted_count,
                created_count=outcome.created_count,
                updated_count=outcome.updated_count,
                duplicate_count=outcome.duplicate_count,
                skipped_count=outcome.skipped_count,
                latency_ms=(perf_counter() - started) * 1000,
            )
            return outcome
        except Exception as exc:
            self._metrics.increment(metric=EXTRACTION_FAILED)
            logger.warning(
                "memory.extraction.failed",
                owner_id=str(event.owner_id),
                runtime=event.runtime,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            if claimed and self._idempotency_client is not None:
                with suppress(Exception):
                    await self._idempotency_client.delete(key)
            raise
        finally:
            self._metrics.record_duration(
                operation=EXTRACTION_LATENCY,
                duration_ms=(perf_counter() - started) * 1000,
            )
