"""Local eligibility checks that avoid an LLM call for low-value turns."""

from __future__ import annotations

import re

from app.ai.memory.policy.models import (
    MemoryExtractionAction,
    MemoryExtractionDecision,
    MemoryTurnEvent,
)
from app.core.settings import settings

_TRIVIAL = {
    "thanks",
    "thank you",
    "ok",
    "okay",
    "great",
    "got it",
    "continue",
    "yes",
    "no",
    "sure",
    "cool",
    "bye",
}
_EXPLICIT = (
    "remember this",
    "remember that",
    "save this",
    "keep this in mind",
    "note this",
    "from now on",
    "going forward",
    "do not forget",
)
_DURABLE = (
    "i prefer",
    "i like",
    "im learning",
    "i am learning",
    "im researching",
    "i am researching",
    "im interested in",
    "i am interested in",
    "i want to learn",
    "my interests include",
    "i do not want",
    "always use",
    "please avoid",
    "my goal is",
    "i am planning",
    "i am building",
    "we decided",
    "we will use",
    "architecture is frozen",
    "benchmark showed",
    "evaluation found",
    "result confirms",
)


class MemoryExtractionPolicy:
    def decide(self, event: MemoryTurnEvent) -> MemoryExtractionDecision:
        if not settings.memory_extraction_policy_enabled:
            return MemoryExtractionDecision(
                action=MemoryExtractionAction.EXTRACT_ASYNC_READY,
                reasons=["policy_disabled"],
            )
        normalized = re.sub(r"[^a-z0-9 ]+", "", event.user_message.lower()).strip()
        if not event.is_final_user_facing_turn or event.runtime not in {"chat", "research"}:
            return MemoryExtractionDecision(
                action=MemoryExtractionAction.SKIP,
                reasons=["non_user_facing_runtime"],
            )
        if not event.assistant_message.strip():
            return MemoryExtractionDecision(
                action=MemoryExtractionAction.SKIP,
                reasons=["empty_assistant_response"],
            )
        if any(signal in normalized for signal in _EXPLICIT):
            return MemoryExtractionDecision(
                action=MemoryExtractionAction.EXTRACT_SYNC,
                reasons=["explicit_memory_intent"],
                explicit_request=True,
            )
        if normalized in _TRIVIAL:
            return MemoryExtractionDecision(
                action=MemoryExtractionAction.SKIP,
                reasons=["trivial_turn"],
            )
        if len(normalized) < settings.memory_extraction_min_user_characters:
            return MemoryExtractionDecision(
                action=MemoryExtractionAction.SKIP,
                reasons=["below_minimum_length"],
            )
        if any(signal in normalized for signal in _DURABLE):
            return MemoryExtractionDecision(
                action=MemoryExtractionAction.EXTRACT_ASYNC_READY,
                reasons=["durable_signal"],
            )
        return MemoryExtractionDecision(
            action=MemoryExtractionAction.SKIP,
            reasons=["no_durable_signal"],
        )
