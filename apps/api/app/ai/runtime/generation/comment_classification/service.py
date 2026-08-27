"""Classifies a feedback comment as objective or preference -- a small,
cheap, bounded LLM call (never the main synthesis/review-tier model),
mirroring `WebSearchNecessityService`'s exact pattern."""

from __future__ import annotations

from uuid import UUID

import structlog
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.generation.comment_classification.models import (
    CommentClassificationDecision,
)
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.models.enums import CommentClassification

logger = structlog.get_logger()

_MAX_COMMENT_CHARACTERS = 2000
_SYSTEM_PROMPT = (
    "You classify a user's feedback comment on an AI-generated answer as "
    "either 'objective' or 'preference'. 'objective' means a factual "
    "quality problem with the answer itself -- wrong or fabricated "
    "citations, incorrect facts, missed the actual question, unsupported "
    "claims. 'preference' means a stylistic or subjective complaint -- "
    "tone, length, formatting, phrasing, or a matter of taste rather than "
    "correctness. When genuinely ambiguous, prefer 'preference' -- it is "
    "the conservative choice, since an objective misclassification can "
    "contaminate a shared quality dataset while a preference "
    "misclassification only stays scoped to one user. Return a one-"
    "sentence reason a reviewer can read. Respond with ONLY a single JSON "
    "object matching the requested schema -- no markdown code fences, no "
    "prose before or after it."
)


class CommentClassificationService:
    """Falls to a cheap OpenAI/Claude model (`cheap_provider`, resolved at
    composition time from whichever of those two is configured -- never
    Groq/Gemini/Ollama for this call). If neither is configured, falls
    through once more to `fallback_generation_runtime` with
    `RoutingStrategy.CLASSIFICATION` (still not `AUTO`, which hard-defaults
    to Groq) so classification is never unavailable, only ever
    de-prioritized to whatever's actually configured."""

    def __init__(
        self,
        *,
        cheap_generation_runtime: GenerationRuntimeInterface,
        cheap_provider: GenerationProvider | None,
        fallback_generation_runtime: GenerationRuntimeInterface | None = None,
    ) -> None:
        self._cheap_runtime = cheap_generation_runtime
        self._cheap_provider = cheap_provider
        self._fallback_runtime = fallback_generation_runtime

    async def classify(
        self,
        *,
        comment: str,
        owner_id: UUID,
        generation_id: UUID,
    ) -> CommentClassificationDecision:
        try:
            return await self._classify_with_model(
                comment=comment,
                owner_id=owner_id,
                generation_id=generation_id,
            )
        except Exception as exc:
            # Fail closed toward the conservative outcome (never contaminate
            # the shared golden set with a misclassified comment) but never
            # fail the feedback submission itself.
            logger.warning(
                "generation.comment_classification.unavailable",
                generation_id=str(generation_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return CommentClassificationDecision(
                classification=CommentClassification.PREFERENCE,
                reason="Classification was unavailable; defaulted to preference.",
            )

    async def _classify_with_model(
        self,
        *,
        comment: str,
        owner_id: UUID,
        generation_id: UUID,
    ) -> CommentClassificationDecision:
        request = GenerationRequest(
            prompt_context=PromptContext(context="", chunks=[]),
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=(
                f"Feedback comment: {comment.strip()[:_MAX_COMMENT_CHARACTERS]}\n"
                "Is this objective or a preference?"
            ),
            response_format=ResponseFormat.STRUCTURED,
            output_model=CommentClassificationDecision,
            # Generous relative to the schema's tiny worst case (~150
            # tokens), matching WebSearchNecessityService's own sizing
            # rationale for the same class of bounded classification call.
            max_tokens=600,
            max_regeneration_attempts=2,
            owner_id=owner_id,
            session_id=generation_id,
            temperature=0.0,
            routing_strategy=(
                RoutingStrategy.CLASSIFICATION if self._cheap_provider is None else None
            ),
            cache_runtime=CacheRuntime.REVIEWER,
            runtime=RuntimeType.RESEARCH,
            metadata={
                "generation_id": str(generation_id),
                "usage_category": "comment_classification_decision",
                "prompt_version": "comment-classification-v1",
            },
        )

        runtime = (
            self._cheap_runtime
            if self._cheap_provider is not None
            else (self._fallback_runtime or self._cheap_runtime)
        )
        result = await runtime.execute(request, provider=self._cheap_provider)
        decision = result.parsed_output
        if isinstance(decision, dict):
            decision = CommentClassificationDecision.model_validate(decision)
        if not isinstance(decision, CommentClassificationDecision):
            raise ValueError("Comment classification did not return a schema-valid decision.")
        return decision
