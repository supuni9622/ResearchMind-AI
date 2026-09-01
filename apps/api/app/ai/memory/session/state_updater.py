"""Session-state distillation -- the "dedicated state updater" referenced
in `state_from_user_turn`'s old docstring (that function and its narrow
trigger-phrase gate are retired in favor of this).

After every Chat/Deep Research turn, this asks a cheap model to maintain
one evolving sentence describing what the session is currently about,
folding in the previous state (if any) plus the new turn. Storing that as
SESSION memory (upserted in place, not appended -- see
`MemoryService.get_latest_session_state`) means a later turn that uses a
pronoun ("it", "that") has something concrete in its memory context to
resolve against, instead of the literal, unresolved pronoun flowing
straight into planning (the production bug this was built to fix,
2026-07-25: a Deep Research follow-up "so how magma related to it?" had
no idea what "it" meant, because nothing about turn 1's topic had ever
been persisted anywhere retrievable).

Mirrors `MemoryExtractionService`'s shape (cheap/bounded Generation Runtime
call, structured output, fail-open) rather than the dedicated-cheap-model-
registry style used by `WebSearchNecessityService`/`PaperQueryExtractionService`
-- this is Memory-Platform-native work, so it follows that platform's own
existing composition precedent (`build_memory_extraction_service()`) rather
than importing a pattern from a different platform.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.context.models import PromptContext
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.services.memory_service import MemoryService
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface

logger = structlog.get_logger()

_MAX_STATE_CHARACTERS = 300

_SYSTEM_PROMPT = f"""You maintain one short, evolving summary of what a conversation session \
is currently about, so a later turn that uses a pronoun ("it", "that", "this topic") can be \
understood without the original context.

You are given the previous summary (if any) and the latest turn (user message + assistant \
reply). Produce an updated summary that:
- names the concrete subject(s) being discussed -- never a pronoun
- folds in what the latest turn adds or changes (a new subtopic, a narrowing of focus, an \
explicit topic change)
- stays factual and short: at most {_MAX_STATE_CHARACTERS} characters, ideally one sentence
- carries forward anything from the previous summary that's still relevant; drops anything the \
conversation has clearly moved on from

Set `has_topic` to false only for turns with no durable subject at all (greetings, thanks, \
small talk, or a one-off question with no follow-on relevance) -- in that case still return the \
previous summary unchanged in `content` if one was supplied, or an empty string if not. Most \
turns do have a topic; false is the exception, not the default.

Return a valid JSON object matching the requested schema. No prose, no markdown fences."""


class SessionStateDistillation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_topic: bool
    content: str = Field(max_length=_MAX_STATE_CHARACTERS)


class SessionStateUpdaterService:
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

    async def distill(
        self,
        *,
        user_message: str,
        assistant_message: str | None = None,
        previous_state: str | None = None,
        owner_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> SessionStateDistillation | None:
        """Best-effort: any failure returns `None` (caller skips writing
        anything this turn) rather than raising -- this must never break
        the turn that already completed."""

        turn = f"User: {user_message}"
        if assistant_message:
            turn += f"\nAssistant: {assistant_message}"

        context = (
            f"Previous summary: {previous_state}\n\n{turn}"
            if previous_state
            else f"Previous summary: (none yet)\n\n{turn}"
        )

        request = GenerationRequest(
            prompt_context=PromptContext(context=context, chunks=[]),
            system_prompt=_SYSTEM_PROMPT,
            user_prompt="Update the session summary from the turn above.",
            owner_id=owner_id,
            session_id=session_id,
            metadata={"usage_category": "session_state_distillation"},
            response_format=ResponseFormat.STRUCTURED,
            output_model=SessionStateDistillation,
            temperature=0.0,
            max_tokens=300,
        )

        try:
            result = await self._generation_runtime.execute(request, provider=self._provider)
        except Exception as exc:
            if self._fallback_provider is None:
                logger.warning(
                    "memory.session_state.generation_failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                return None
            logger.warning(
                "memory.session_state.primary_generation_failed",
                provider=self._provider.value if self._provider else None,
                fallback_provider=self._fallback_provider.value,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            try:
                result = await self._generation_runtime.execute(
                    request, provider=self._fallback_provider
                )
            except Exception as fallback_exc:
                logger.warning(
                    "memory.session_state.fallback_generation_failed",
                    provider=self._fallback_provider.value,
                    error_type=type(fallback_exc).__name__,
                    error=str(fallback_exc),
                )
                return None

        distillation = result.parsed_output
        if isinstance(distillation, dict):
            try:
                distillation = SessionStateDistillation.model_validate(distillation)
            except Exception as exc:
                logger.warning(
                    "memory.session_state.parse_failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                return None

        if not isinstance(distillation, SessionStateDistillation):
            logger.warning(
                "memory.session_state.no_structured_output",
                parsed_output_type=type(distillation).__name__,
            )
            return None

        return distillation


_CURRENT_TOPIC_KIND = "current_topic"


async def distill_and_upsert_session_state(
    *,
    memory_service: MemoryService,
    session_state_updater: SessionStateUpdaterService,
    owner_id: UUID,
    session_id: UUID,
    user_message: str,
    assistant_message: str,
    turn_id: str,
    scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
    project_id: UUID | None = None,
) -> None:
    """Shared by Chat and Deep Research's `_extract_and_store_memory`: look
    up the session's existing `current_topic` state (if any), distill an
    updated one from this turn, and upsert it -- `update_memory()` when a
    prior record exists (in place, no growth), `remember()` for the first
    one. Never raises; callers already wrap memory work in a best-effort
    `try/except`, so failures here surface the same way a distillation or
    storage error always has.

    `scope_type`/`project_id` default to personal -- only Chat conversations
    belonging to a project pass `PROJECT` scope; Deep Research and personal
    Chat turns are unaffected."""

    previous = await memory_service.get_latest_session_state(
        owner_id=owner_id,
        session_id=session_id,
        kind=_CURRENT_TOPIC_KIND,
        scope_type=scope_type,
        project_id=project_id,
    )
    distillation = await session_state_updater.distill(
        user_message=user_message,
        assistant_message=assistant_message,
        previous_state=previous.content if previous is not None else None,
        owner_id=owner_id,
        session_id=session_id,
    )
    if distillation is None or not distillation.has_topic or not distillation.content:
        return

    if previous is not None:
        await memory_service.update_memory(
            owner_id=owner_id,
            memory_id=previous.id,
            type=MemoryType.SESSION,
            scope_type=scope_type,
            project_id=project_id,
            content=distillation.content,
            metadata={"kind": _CURRENT_TOPIC_KIND, "source_turn_id": turn_id},
        )
    else:
        await memory_service.remember(
            owner_id=owner_id,
            type=MemoryType.SESSION,
            scope_type=scope_type,
            project_id=project_id,
            content=distillation.content,
            session_id=session_id,
            metadata={"kind": _CURRENT_TOPIC_KIND, "source_turn_id": turn_id},
        )
