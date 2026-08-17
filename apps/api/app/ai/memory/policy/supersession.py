"""Preference supersession (staleness fix, Wave 2 follow-up) -- decides
whether a new USER preference statement replaces an existing one rather
than being stored alongside it forever.

`MemoryService.remember_extracted()`'s dedup was exact-content-match
only: two preferences that mean the same thing in different words, or
that flatly contradict each other (e.g. "prefers concise answers" ->
later "prefers detailed answers"), both persisted as separate rows with
no supersession -- the prompt-injection read side had no choice but to
show the model both and let it silently reconcile the contradiction
itself, every single turn.

A small, cheap, bounded LLM call -- never the main synthesis/review-tier
model -- same pattern as `CommentClassificationService`/
`WebSearchNecessityService`/`MemoryExtractionService`. Only ever compares
a new statement against one owner's own existing USER preferences (a
handful of rows via `UserMemoryService.list_preferences()`), never across
owners.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from app.ai.knowledge.context.models import PromptContext
from app.ai.memory.models import MemoryRecord
from app.ai.memory.policy.models import (
    PreferenceSupersessionDecision,
    PreferenceTopicClassification,
)
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface

logger = structlog.get_logger()

_MAX_CANDIDATES = 20
_TOPIC_SYSTEM_PROMPT = (
    "Extract a stable lookup topic for one user preference. preference_key must "
    "be a short lowercase snake_case category such as response_length, citation_style, "
    "color_theme, preferred_model, or research_topic. search_terms must contain one to "
    "five short nouns or noun phrases likely to occur in an older preference on the same "
    "topic, including common synonyms where useful. These values only retrieve candidates; "
    "they never authorize overwriting. Return only the requested structured JSON."
)
_SYSTEM_PROMPT = (
    "You compare a NEW user-preference statement against a numbered list "
    "of a user's EXISTING stored preferences. Decide whether the new "
    "statement updates or contradicts exactly one existing preference on "
    "the same topic -- for example NEW 'prefers detailed answers' "
    "supersedes EXISTING 'prefers concise answers'. If so, return that "
    "item's number. If the new statement is about a different topic, is "
    "additive rather than contradictory, or you are not confident, "
    "return 0 -- 0 is the safe default: wrongly overwriting a still-valid "
    "distinct preference loses information, while wrongly keeping both "
    "merely leaves one redundant row. Respond with ONLY a single JSON "
    "object matching the requested schema -- no markdown code fences, no "
    "prose before or after it."
)


@dataclass(frozen=True)
class PreferenceSupersessionMatch:
    record: MemoryRecord
    reason: str


class PreferenceSupersessionService:
    def __init__(
        self,
        generation_runtime: GenerationRuntimeInterface,
        *,
        provider: GenerationProvider | None = None,
        fallback_provider: GenerationProvider | None = None,
    ) -> None:
        self._generation_runtime = generation_runtime
        self._provider = provider
        self._fallback_provider = fallback_provider

    async def find_superseded(
        self,
        *,
        owner_id: UUID,
        new_content: str,
        existing: list[MemoryRecord],
    ) -> PreferenceSupersessionMatch | None:
        if not existing:
            return None

        candidates = existing[:_MAX_CANDIDATES]
        request = self._build_request(owner_id, new_content, candidates)

        decision = await self._decide(request, self._provider)
        if decision is None and self._fallback_provider is not None:
            decision = await self._decide(request, self._fallback_provider)

        if decision is None or decision.superseded_index == 0:
            return None

        index = decision.superseded_index - 1
        if not 0 <= index < len(candidates):
            logger.warning(
                "memory.supersession.index_out_of_range",
                index=decision.superseded_index,
                candidate_count=len(candidates),
            )
            return None

        return PreferenceSupersessionMatch(record=candidates[index], reason=decision.reason)

    async def classify_topic(
        self,
        *,
        owner_id: UUID,
        new_content: str,
    ) -> PreferenceTopicClassification | None:
        request = GenerationRequest(
            prompt_context=PromptContext(context="", chunks=[]),
            system_prompt=_TOPIC_SYSTEM_PROMPT,
            user_prompt=f"Preference: {new_content.strip()}",
            response_format=ResponseFormat.STRUCTURED,
            output_model=PreferenceTopicClassification,
            max_tokens=250,
            max_regeneration_attempts=2,
            temperature=0.0,
            owner_id=owner_id,
            metadata={"usage_category": "preference_topic_classification"},
        )
        topic = await self._classify_topic(request, self._provider)
        if topic is None and self._fallback_provider is not None:
            topic = await self._classify_topic(request, self._fallback_provider)
        return topic

    async def _classify_topic(
        self,
        request: GenerationRequest,
        provider: GenerationProvider | None,
    ) -> PreferenceTopicClassification | None:
        try:
            result = await self._generation_runtime.execute(request, provider=provider)
            topic = result.parsed_output
            if isinstance(topic, dict):
                topic = PreferenceTopicClassification.model_validate(topic)
            if not isinstance(topic, PreferenceTopicClassification):
                return None
            cleaned_terms = [
                " ".join(term.lower().split())[:100] for term in topic.search_terms if term.strip()
            ]
            if not cleaned_terms:
                return None
            return topic.model_copy(
                update={
                    "preference_key": topic.preference_key.strip().lower().replace(" ", "_")[:100],
                    "search_terms": cleaned_terms[:5],
                }
            )
        except Exception as exc:
            logger.warning(
                "memory.supersession.topic_classification_failed",
                provider=provider.value if provider else None,
                error_type=type(exc).__name__,
            )
            return None

    async def _decide(
        self,
        request: GenerationRequest,
        provider: GenerationProvider | None,
    ) -> PreferenceSupersessionDecision | None:
        try:
            result = await self._generation_runtime.execute(request, provider=provider)
        except Exception as exc:
            logger.warning(
                "memory.supersession.generation_failed",
                provider=provider.value if provider else None,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return None

        decision = result.parsed_output
        if isinstance(decision, dict):
            try:
                decision = PreferenceSupersessionDecision.model_validate(decision)
            except Exception as exc:
                logger.warning(
                    "memory.supersession.parse_failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                return None

        if not isinstance(decision, PreferenceSupersessionDecision):
            logger.warning(
                "memory.supersession.no_structured_output",
                parsed_output_type=type(decision).__name__,
            )
            return None

        return decision

    @staticmethod
    def _build_request(
        owner_id: UUID,
        new_content: str,
        candidates: list[MemoryRecord],
    ) -> GenerationRequest:
        numbered = "\n".join(f"{i + 1}. {memory.content}" for i, memory in enumerate(candidates))
        return GenerationRequest(
            prompt_context=PromptContext(context="", chunks=[]),
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=(
                f"NEW: {new_content.strip()}\n\nEXISTING:\n{numbered}\n\n"
                "Which existing item (if any) does NEW supersede?"
            ),
            response_format=ResponseFormat.STRUCTURED,
            output_model=PreferenceSupersessionDecision,
            max_tokens=300,
            max_regeneration_attempts=2,
            temperature=0.0,
            owner_id=owner_id,
            metadata={"usage_category": "preference_supersession"},
        )
