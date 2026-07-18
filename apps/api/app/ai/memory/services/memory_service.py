"""
MemoryService (PRD §9.1) -- the platform's single orchestration layer:
remember, recall, search, forget, update. Routes each call to the
type-specific service (`SessionMemoryService`, `UserMemoryService`,
`SemanticMemoryService`, `ResearchMemoryService`) that actually owns
the storage backend for that `MemoryType` (PRD §7).

Every type-specific service exposes the same `recall`/`forget`/
`update` shape, which lets `recall()`/`forget()`/`update_memory()`
dispatch generically when the caller doesn't know a memory's type
(the `GET/PUT/DELETE /memory/{id}` HTTP contract has no type in the
path) -- `remember()` is the one exception, since only SESSION memory
needs an extra `session_id`.

SESSION memory is deliberately excluded from `search()`: Valkey has no
reverse index from owner to every session a record was written under
(see `ValkeySessionStore`), so a conversation's history is only
reachable via `get_context(session_id=...)`, not free-text search.
USER memory has no embedding index (PRD §6.2), so its `search()`
branch is a recency listing, not a ranked query match.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Protocol
from uuid import UUID

import structlog

from app.ai.memory.artifacts.builders import MemoryArtifactBuilder
from app.ai.memory.artifacts.writers import MemoryArtifactWriter
from app.ai.memory.enums import MemoryType
from app.ai.memory.exceptions import MemoryValidationError
from app.ai.memory.importance import score_importance
from app.ai.memory.models import (
    MemoryContext,
    MemoryRecord,
    MemorySearchRequest,
    MemorySearchResult,
)
from app.ai.memory.observability.metrics import (
    MEMORY_COUNT,
    MEMORY_HITS,
    MEMORY_MISSES,
    REMEMBER_LATENCY,
    SEARCH_LATENCY,
)
from app.ai.memory.profile.service import UserMemoryService
from app.ai.memory.research.service import ResearchMemoryService
from app.ai.memory.retrieval.fusion import reciprocal_rank_fusion
from app.ai.memory.semantic.service import SemanticMemoryService
from app.ai.memory.session.service import SessionMemoryService
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder

logger = structlog.get_logger()

_DEFAULT_IMPORTANCE_THRESHOLD = 0.1


class _MemoryBackend(Protocol):
    """
    The `recall`/`forget`/`update` shape every type-specific service
    shares -- lets `MemoryService._registry` be typed precisely instead
    of `dict[MemoryType, Any]` (`remember`/`search` aren't part of this
    protocol: their signatures diverge per type, so those are called
    directly on the specific service instead of through the registry).
    """

    async def recall(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
    ) -> MemoryRecord | None: ...

    async def forget(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
    ) -> bool: ...

    async def update(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float | None = None,
    ) -> MemoryRecord | None: ...


class _RememberableBackend(Protocol):
    """
    The `remember()` shape shared by `UserMemoryService`,
    `SemanticMemoryService`, and `ResearchMemoryService` -- SESSION is
    excluded (its `remember()` requires an extra `session_id`), so
    `MemoryService.remember()` dispatches to `self._session` directly
    instead of through this protocol.
    """

    async def remember(
        self,
        *,
        owner_id: UUID,
        content: str,
        importance_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord: ...


class MemoryService:
    def __init__(
        self,
        *,
        session_memory: SessionMemoryService,
        user_memory: UserMemoryService,
        semantic_memory: SemanticMemoryService,
        research_memory: ResearchMemoryService,
        artifact_writer: MemoryArtifactWriter | None = None,
        metrics: MetricsRecorder | None = None,
        importance_threshold: float = _DEFAULT_IMPORTANCE_THRESHOLD,
    ) -> None:
        self._session = session_memory
        self._user = user_memory
        self._semantic = semantic_memory
        self._research = research_memory

        self._registry: dict[MemoryType, _MemoryBackend] = {
            MemoryType.SESSION: self._session,
            MemoryType.USER: self._user,
            MemoryType.SEMANTIC: self._semantic,
            MemoryType.RESEARCH: self._research,
        }

        self._rememberable: dict[MemoryType, _RememberableBackend] = {
            MemoryType.USER: self._user,
            MemoryType.SEMANTIC: self._semantic,
            MemoryType.RESEARCH: self._research,
        }

        self._artifact_writer = artifact_writer
        self._metrics = metrics or NoOpMetricsRecorder()
        self._importance_threshold = importance_threshold

    # ==========================================================
    # Remember
    # ==========================================================

    async def remember(
        self,
        *,
        owner_id: UUID,
        type: MemoryType,
        content: str,
        session_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float | None = None,
    ) -> MemoryRecord | None:
        """
        Returns `None` (skipping persistence) when the computed/supplied
        importance score falls below `importance_threshold` -- PRD §16's
        "avoid remembering everything".
        """

        score = importance_score if importance_score is not None else score_importance(content)

        if score < self._importance_threshold:
            logger.info(
                "memory.remember.skipped_low_importance",
                owner_id=str(owner_id),
                type=type.value,
                importance_score=score,
            )
            return None

        started = perf_counter()

        if type == MemoryType.SESSION:
            if session_id is None:
                raise MemoryValidationError("session_id is required to remember SESSION memory.")

            record = await self._session.remember(
                owner_id=owner_id,
                session_id=session_id,
                content=content,
                importance_score=score,
                metadata=metadata,
            )
        else:
            record = await self._rememberable[type].remember(
                owner_id=owner_id,
                content=content,
                importance_score=score,
                metadata=metadata,
            )

        self._metrics.record_duration(
            operation=REMEMBER_LATENCY,
            duration_ms=(perf_counter() - started) * 1000,
        )
        self._metrics.increment(metric=MEMORY_COUNT)

        return record

    # ==========================================================
    # Recall / Forget / Update
    # ==========================================================

    async def recall(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        type: MemoryType | None = None,
    ) -> MemoryRecord | None:
        if type is not None:
            return await self._registry[type].recall(owner_id=owner_id, memory_id=memory_id)

        for service in self._registry.values():
            record = await service.recall(owner_id=owner_id, memory_id=memory_id)

            if record is not None:
                return record

        return None

    async def forget(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        type: MemoryType | None = None,
    ) -> bool:
        if type is not None:
            return await self._registry[type].forget(owner_id=owner_id, memory_id=memory_id)

        for service in self._registry.values():
            if await service.forget(owner_id=owner_id, memory_id=memory_id):
                return True

        return False

    async def update_memory(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        type: MemoryType | None = None,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float | None = None,
    ) -> MemoryRecord | None:
        services = [self._registry[type]] if type is not None else list(self._registry.values())

        for service in services:
            updated = await service.update(
                owner_id=owner_id,
                memory_id=memory_id,
                content=content,
                metadata=metadata,
                importance_score=importance_score,
            )

            if updated is not None:
                return updated

        return None

    # ==========================================================
    # Search
    # ==========================================================

    async def search(
        self,
        request: MemorySearchRequest,
    ) -> MemorySearchResult:
        started = perf_counter()

        vector_backed_services = {
            MemoryType.SEMANTIC: self._semantic,
            MemoryType.RESEARCH: self._research,
        }

        result_lists: list[list[MemoryRecord]] = []

        for memory_type in request.memory_types:
            if memory_type == MemoryType.SESSION:
                continue

            if memory_type == MemoryType.USER:
                result_lists.append(
                    await self._user.list_preferences(
                        owner_id=request.owner_id,
                        limit=request.top_k,
                    )
                )
                continue

            result_lists.append(
                await vector_backed_services[memory_type].search(
                    owner_id=request.owner_id,
                    query=request.query,
                    top_k=request.top_k,
                )
            )

        # Merge -> deduplicate -> rerank (PRD's Retrieval Pipeline):
        # each list above is already best-first ranked by its own
        # service, so combine by rank rather than crushing them all
        # into one `importance_score` sort (see `retrieval/fusion.py`).
        memories = reciprocal_rank_fusion(result_lists)[: request.top_k]

        result = MemorySearchResult(
            memories=memories,
            latency_ms=(perf_counter() - started) * 1000,
        )

        self._metrics.record_duration(
            operation=SEARCH_LATENCY,
            duration_ms=result.latency_ms,
        )
        self._metrics.increment(metric=MEMORY_HITS if memories else MEMORY_MISSES)

        await self._persist_search_artifact(request=request, result=result)

        return result

    # ==========================================================
    # Context
    # ==========================================================

    async def get_context(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        semantic_query: str | None = None,
        top_k: int = 10,
    ) -> MemoryContext:
        session_memories = await self._session.get_context(
            owner_id=owner_id,
            session_id=session_id,
            limit=top_k,
        )

        semantic_memories: list[MemoryRecord] = []
        research_memories: list[MemoryRecord] = []

        if semantic_query:
            semantic_memories = await self._semantic.search(
                owner_id=owner_id,
                query=semantic_query,
                top_k=top_k,
            )
            research_memories = await self._research.search(
                owner_id=owner_id,
                query=semantic_query,
                top_k=top_k,
            )

        context = MemoryContext(
            session_memories=session_memories,
            semantic_memories=semantic_memories,
            research_memories=research_memories,
        )

        await self._persist_context_artifact(
            owner_id=owner_id,
            session_id=session_id,
            context=context,
        )

        return context

    # ==========================================================
    # Internal
    # ==========================================================

    async def _persist_search_artifact(
        self,
        *,
        request: MemorySearchRequest,
        result: MemorySearchResult,
    ) -> None:
        if self._artifact_writer is None:
            return

        try:
            artifact = MemoryArtifactBuilder().build_search(
                owner_id=request.owner_id,
                query=request.query,
                memory_types=request.memory_types,
                result=result,
            )

            await self._artifact_writer.write_search(artifact)
        except Exception as exc:
            logger.warning(
                "memory.artifacts.search_persist_failed",
                owner_id=str(request.owner_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )

    async def _persist_context_artifact(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        context: MemoryContext,
    ) -> None:
        if self._artifact_writer is None:
            return

        try:
            artifact = MemoryArtifactBuilder().build_context(
                owner_id=owner_id,
                session_id=session_id,
                context=context,
            )

            await self._artifact_writer.write_context(artifact)
        except Exception as exc:
            logger.warning(
                "memory.artifacts.context_persist_failed",
                owner_id=str(owner_id),
                session_id=str(session_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
