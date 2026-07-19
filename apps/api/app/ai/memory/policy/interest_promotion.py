"""Cheap, privacy-scoped promotion of repeated research-topic engagement."""

from __future__ import annotations

import re
from hashlib import blake2b
from uuid import UUID

import structlog
from redis.asyncio import Redis

from app.core.settings import settings

logger = structlog.get_logger()

_TOKEN = re.compile(r"[a-z][a-z0-9_-]{2,}", re.IGNORECASE)
_STOP_WORDS = frozenset(
    {
        "about",
        "after",
        "also",
        "and",
        "are",
        "can",
        "could",
        "does",
        "for",
        "from",
        "have",
        "help",
        "how",
        "into",
        "like",
        "make",
        "need",
        "please",
        "question",
        "should",
        "that",
        "the",
        "this",
        "use",
        "using",
        "want",
        "what",
        "when",
        "with",
        "would",
        "your",
    }
)
_MAX_TOPICS_PER_TURN = 3


class RepeatedInterestPromotionService:
    """Promote a topic only after distinct-session engagement.

    This is deliberately lexical and bounded: it is an inexpensive candidate
    gate, not a semantic classifier. The LLM still validates whether the
    promoted candidate should become a durable USER memory.
    """

    def __init__(self, client: Redis | None = None) -> None:
        self._client = client

    async def promoted_topics(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        user_message: str,
    ) -> list[str]:
        if not settings.memory_interest_promotion_enabled or self._client is None:
            return []

        topics = _topic_tokens(user_message)
        if not topics:
            return []

        try:
            pipeline = self._client.pipeline(transaction=False)
            for topic in topics:
                key = self._key(owner_id, topic)
                pipeline.sadd(key, str(session_id))
                pipeline.scard(key)
                pipeline.expire(key, settings.memory_interest_promotion_ttl_seconds)
            results = await pipeline.execute()
        except Exception as exc:
            logger.warning(
                "memory.interest_promotion.unavailable",
                owner_id=str(owner_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return []

        threshold = settings.memory_interest_promotion_min_distinct_sessions
        candidates = [
            topic
            for index, topic in enumerate(topics)
            # Only the newly observed session can cause a promotion. This
            # prevents every later message in the same conversation from
            # becoming eligible for the same topic.
            if bool(results[index * 3]) and int(results[index * 3 + 1]) >= threshold
        ]
        if not candidates:
            return []

        try:
            claim_pipeline = self._client.pipeline(transaction=False)
            for topic in candidates:
                claim_pipeline.set(
                    self._claim_key(owner_id, topic),
                    "1",
                    ex=settings.memory_interest_promotion_ttl_seconds,
                    nx=True,
                )
            claims = await claim_pipeline.execute()
        except Exception as exc:
            logger.warning(
                "memory.interest_promotion.claim_unavailable",
                owner_id=str(owner_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return []

        # One topic is eligible for one LLM validation in its retention
        # window. Exact-memory de-duplication remains a second safety net,
        # but this avoids paying for repeated validation in new sessions.
        promoted = [topic for topic, claim in zip(candidates, claims, strict=True) if bool(claim)]
        if promoted:
            logger.info(
                "memory.interest_promotion.eligible",
                owner_id=str(owner_id),
                topics=promoted,
                threshold=threshold,
            )
        return promoted

    @staticmethod
    def _key(owner_id: UUID, topic: str) -> str:
        # Topic text must not be exposed in operational Redis keys.
        digest = blake2b(topic.encode(), digest_size=12).hexdigest()
        return f"memory:interest-sessions:{owner_id}:{digest}"

    @staticmethod
    def _claim_key(owner_id: UUID, topic: str) -> str:
        digest = blake2b(topic.encode(), digest_size=12).hexdigest()
        return f"memory:interest-promoted:{owner_id}:{digest}"


def _topic_tokens(message: str) -> list[str]:
    """Return a small ordered set of meaningful lexical topic candidates."""

    topics: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN.finditer(message.lower()):
        token = match.group(0)
        if token in _STOP_WORDS or token in seen:
            continue
        seen.add(token)
        topics.append(token)
        if len(topics) == _MAX_TOPICS_PER_TURN:
            break
    return topics
