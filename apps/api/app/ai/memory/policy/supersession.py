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
    PreferenceKind,
    PreferenceSupersessionDecision,
    PreferenceTopicClassification,
)
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface

logger = structlog.get_logger()

_MAX_CANDIDATES = 20
_TOPIC_SYSTEM_PROMPT = (
    "Extract lookup hints and typed attributes for one user preference. Use a controlled "
    "preference_kind when it is response_length, tone, citation_style, preferred_model, "
    "or preferred_tool; otherwise use custom. For controlled kinds preference_key must "
    "equal preference_kind. For custom use a short lowercase snake_case topic key. "
    "normalized_value must contain only the preferred value, not a sentence. Choose the "
    "value_type describing that value. confidence estimates classification confidence, "
    "and explicit is true only when the user directly stated the preference rather than "
    "it being inferred from behavior or interests. search_terms must contain one to "
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
            max_tokens=400,
            max_regeneration_attempts=2,
            temperature=0.0,
            owner_id=owner_id,
            metadata={"usage_category": "preference_topic_classification"},
        )
        topic = await self._classify_topic(request, self._provider)
        if topic is None and self._fallback_provider is not None:
            topic = await self._classify_topic(request, self._fallback_provider)
        return topic

    @staticmethod
    def find_deterministic_superseded(
        *,
        classification: PreferenceTopicClassification,
        existing: list[MemoryRecord],
        confidence_threshold: float,
    ) -> PreferenceSupersessionMatch | None:
        """Match one already-typed controlled preference without another LLM call.

        Custom or inferred preferences remain on the conservative judge path.
        Multiple typed rows indicate legacy ambiguity and also defer to the judge.
        """

        if (
            classification.preference_kind == PreferenceKind.CUSTOM
            or not classification.explicit
            or classification.confidence < confidence_threshold
        ):
            return None

        matches = [
            record
            for record in existing
            if isinstance(record.metadata.get("preference"), dict)
            and record.metadata["preference"].get("schema_version") == "v1"
            and record.metadata["preference"].get("key") == classification.preference_key
        ]
        if len(matches) != 1:
            return None
        return PreferenceSupersessionMatch(
            record=matches[0],
            reason="deterministic_typed_preference_key_match",
        )

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
            cleaned_key = "_".join(
                part
                for part in "".join(
                    char if char.isalnum() else "_" for char in topic.preference_key.lower()
                ).split("_")
                if part
            )[:100]
            if topic.preference_kind != PreferenceKind.CUSTOM:
                cleaned_key = topic.preference_kind.value
            cleaned_value = " ".join(topic.normalized_value.strip().split())[:200]
            if not cleaned_key or not cleaned_value:
                return None
            return topic.model_copy(
                update={
                    "preference_key": cleaned_key,
                    "normalized_value": cleaned_value,
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
