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

import asyncio
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Protocol
from uuid import UUID

import structlog

from app.ai.memory.artifacts.builders import MemoryArtifactBuilder
from app.ai.memory.artifacts.writers import MemoryArtifactWriter
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.exceptions import MemoryValidationError
from app.ai.memory.importance import score_importance
from app.ai.memory.models import (
    MemoryContext,
    MemoryRecord,
    MemorySearchRequest,
    MemorySearchResult,
)
from app.ai.memory.observability.metrics import (
    CONTEXT_DURABLE_AVAILABLE,
    CONTEXT_DURABLE_EMPTY,
    CONTEXT_LATENCY,
    CONTEXT_REQUESTS,
    CONTEXT_RETRIEVAL_SKIPPED,
    DURABLE_SEARCH_LATENCY,
    MEMORY_COUNT,
    MEMORY_CREATED,
    MEMORY_DUPLICATE,
    MEMORY_HITS,
    MEMORY_MISSES,
    MEMORY_SUPERSEDED,
    MEMORY_UPDATED,
    PARALLEL_SEARCH,
    REMEMBER_LATENCY,
    RESEARCH_SEARCH,
    SEARCH_LATENCY,
    SEMANTIC_SEARCH,
    SESSION_DUPLICATES_REMOVED,
    SESSION_ITEMS_LOADED,
)
from app.ai.memory.policy.models import PreferenceTopicClassification, PreferenceValueType
from app.ai.memory.policy.supersession import (
    PreferenceSupersessionMatch,
    PreferenceSupersessionService,
)
from app.ai.memory.profile.service import UserMemoryService
from app.ai.memory.research.service import ResearchMemoryService
from app.ai.memory.retrieval.availability import DurableMemoryAvailabilityService
from app.ai.memory.retrieval.fusion import reciprocal_rank_fusion
from app.ai.memory.semantic.service import SemanticMemoryService
from app.ai.memory.session.service import SessionMemoryService
from app.core.settings import settings
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder
from app.repositories.memory_settings import MemoryScopeSettingsRepository

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
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> MemoryRecord | None: ...

    async def forget(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> bool: ...

    async def update(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
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
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
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
        availability_service: DurableMemoryAvailabilityService | None = None,
        supersession_service: PreferenceSupersessionService | None = None,
        scope_settings: MemoryScopeSettingsRepository | None = None,
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
        self._availability = availability_service
        self._supersession = supersession_service
        self._scope_settings = scope_settings

    async def list_memories(
        self,
        *,
        owner_id: UUID,
        memory_types: list[MemoryType] | None = None,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        search: str | None = None,
        source: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        origin: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[MemoryRecord], int]:
        """List the authenticated owner's canonical durable memories.

        SESSION data remains session-bound in Valkey and is not enumerable.
        """

        selected_types = memory_types or [
            MemoryType.USER,
            MemoryType.SEMANTIC,
            MemoryType.RESEARCH,
        ]
        if MemoryType.SESSION in selected_types:
            raise MemoryValidationError("SESSION memory cannot be listed outside a session.")
        return await self._user.list_management_page(
            owner_id=owner_id,
            memory_types=selected_types,
            scope_type=scope_type,
            project_id=project_id,
            search=search,
            source=source,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            origin=origin,
            limit=limit,
            offset=offset,
        )

    async def list_user_memories(self, **kwargs: Any) -> tuple[list[MemoryRecord], int]:
        """Backward-compatible USER-only management listing."""

        return await self.list_memories(memory_types=[MemoryType.USER], **kwargs)

    # ==========================================================
    # Remember
    # ==========================================================

    async def remember(
        self,
        *,
        owner_id: UUID,
        type: MemoryType,
        content: str,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
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

        scope_count = (
            await self._user.count_scope(
                owner_id=owner_id, scope_type=scope_type, project_id=project_id
            )
            if type != MemoryType.SESSION
            else 0
        )
        if (
            isinstance(scope_count, int)
            and scope_count >= settings.memory_scope_max_durable_records
        ):
            raise MemoryValidationError(
                "Memory capacity reached for this scope. Delete or export "
                "memories before adding more."
            )

        started = perf_counter()

        if type == MemoryType.SESSION:
            if session_id is None:
                raise MemoryValidationError("session_id is required to remember SESSION memory.")

            record = await self._session.remember(
                owner_id=owner_id,
                session_id=session_id,
                scope_type=scope_type,
                project_id=project_id,
                content=content,
                importance_score=score,
                metadata=metadata,
            )
        else:
            record = await self._rememberable[type].remember(
                owner_id=owner_id,
                scope_type=scope_type,
                project_id=project_id,
                content=content,
                importance_score=score,
                metadata=metadata,
            )

        self._metrics.record_duration(
            operation=REMEMBER_LATENCY,
            duration_ms=(perf_counter() - started) * 1000,
        )
        self._metrics.increment(metric=MEMORY_COUNT)

        if type in {MemoryType.SEMANTIC, MemoryType.RESEARCH} and self._availability is not None:
            await self._availability.invalidate(
                owner_id=owner_id, scope_type=scope_type, project_id=project_id
            )

        return record

    async def remember_extracted(
        self,
        *,
        owner_id: UUID,
        type: MemoryType,
        content: str,
        importance_score: float,
        metadata: dict[str, Any],
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> tuple[MemoryRecord | None, str]:
        """Persist an extracted durable memory without duplicating facts.

        Exact normalized duplicates are updated only with provenance (rather
        than creating another row). For USER preferences specifically, a
        second tier catches near-duplicates exact matching misses: a cheap
        LLM call (`PreferenceSupersessionService`) checks whether the new
        statement replaces an existing preference on the same topic (e.g.
        "prefers detailed answers" replacing "prefers concise answers") and,
        if so, updates that row in place instead of creating a second,
        contradictory one. RESEARCH findings are additive facts, not
        preferences that flip -- this tier is USER-only.
        """

        if not await self._capture_enabled(owner_id, scope_type, project_id):
            logger.info("memory.capture.disabled", owner_id=str(owner_id), scope=scope_type.value)
            return None, "capture_disabled"
        if type not in {MemoryType.USER, MemoryType.RESEARCH}:
            raise MemoryValidationError("Only USER and RESEARCH extracted memories are allowed.")
        service = self._user if type == MemoryType.USER else self._research
        existing = await service.find_exact_content(
            owner_id=owner_id,
            content=content,
            scope_type=scope_type,
            project_id=project_id,
        )
        if existing is not None:
            updated = await service.update(
                owner_id=owner_id,
                memory_id=existing.id,
                scope_type=scope_type,
                project_id=project_id,
                metadata=metadata,
                importance_score=max(existing.importance_score, importance_score),
            )
            self._metrics.increment(metric=MEMORY_DUPLICATE)
            self._metrics.increment(metric=MEMORY_UPDATED)
            return updated, "duplicate"

        if (
            type == MemoryType.USER
            and self._supersession is not None
            and settings.memory_preference_supersession_enabled
        ):
            supersession_match, classification = await self._find_superseded_preference(
                owner_id=owner_id,
                content=content,
                scope_type=scope_type,
                project_id=project_id,
            )
            if classification is not None:
                metadata = self._with_typed_preference_metadata(metadata, classification)
            if supersession_match is not None:
                superseded = supersession_match.record
                metadata = {
                    **metadata,
                    "_supersession": {
                        "replaced_memory_id": str(superseded.id),
                        "reason": supersession_match.reason,
                        "decided_at": datetime.now(UTC).isoformat(),
                    },
                }
                updated = await self._user.update(
                    owner_id=owner_id,
                    memory_id=superseded.id,
                    scope_type=scope_type,
                    project_id=project_id,
                    content=content,
                    metadata=metadata,
                    importance_score=importance_score,
                )
                if updated is not None:
                    self._metrics.increment(metric=MEMORY_SUPERSEDED)
                    self._metrics.increment(metric=MEMORY_UPDATED)
                    return updated, "superseded"

        record = await self.remember(
            owner_id=owner_id,
            type=type,
            content=content,
            scope_type=scope_type,
            project_id=project_id,
            importance_score=importance_score,
            metadata=metadata,
        )
        if record is None:
            return None, "skipped"
        self._metrics.increment(metric=MEMORY_CREATED)
        return record, "created"

    async def _find_superseded_preference(
        self,
        *,
        owner_id: UUID,
        content: str,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> tuple[PreferenceSupersessionMatch | None, PreferenceTopicClassification | None]:
        if self._supersession is None:
            return None, None
        try:
            topic = await self._supersession.classify_topic(
                owner_id=owner_id,
                new_content=content,
            )
            if topic is not None:
                candidates = await self._user.find_preference_candidates(
                    owner_id=owner_id,
                    scope_type=scope_type,
                    project_id=project_id,
                    preference_key=topic.preference_key,
                    search_terms=topic.search_terms,
                    limit=settings.memory_preference_candidate_limit,
                )
            else:
                # Provider failure must not block memory creation. Preserve a
                # small version of the old recency behavior as a fail-open
                # fallback without restoring the recent-20 blind spot.
                candidates = await self._user.list_preferences(
                    owner_id=owner_id,
                    scope_type=scope_type,
                    project_id=project_id,
                    limit=settings.memory_preference_recent_fallback_limit,
                )
            match = None
            if topic is not None:
                match = PreferenceSupersessionService.find_deterministic_superseded(
                    classification=topic,
                    existing=candidates,
                    confidence_threshold=settings.memory_preference_typed_confidence_threshold,
                )
            if match is None:
                match = await self._supersession.find_superseded(
                    owner_id=owner_id,
                    new_content=content,
                    existing=candidates,
                )
            return match, topic
        except Exception as exc:
            logger.warning(
                "memory.supersession.check_failed",
                owner_id=str(owner_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return None, None

    @staticmethod
    def _with_typed_preference_metadata(
        metadata: dict[str, Any],
        classification: PreferenceTopicClassification,
    ) -> dict[str, Any]:
        """Add M10 attributes without replacing the prompt-friendly content."""

        provenance_keys = (
            "feedback_id",
            "generation_id",
            "conversation_id",
            "research_id",
            "turn_id",
        )
        provenance = {
            key: str(metadata[key]) for key in provenance_keys if metadata.get(key) is not None
        }
        value: str | int | bool = classification.normalized_value
        value_type = classification.value_type
        if value_type == PreferenceValueType.INTEGER:
            try:
                value = int(classification.normalized_value)
            except ValueError:
                value_type = PreferenceValueType.STRING
        elif value_type == PreferenceValueType.BOOLEAN:
            normalized = classification.normalized_value.lower()
            if normalized in {"true", "yes", "on", "enabled"}:
                value = True
            elif normalized in {"false", "no", "off", "disabled"}:
                value = False
            else:
                value_type = PreferenceValueType.STRING
        return {
            **metadata,
            # Preserve M9's indexed lookup field for old/new row compatibility.
            "preference_key": classification.preference_key,
            "preference": {
                "schema_version": "v1",
                "kind": classification.preference_kind.value,
                "key": classification.preference_key,
                "value": value,
                "value_type": value_type.value,
                "confidence": classification.confidence,
                "explicit": classification.explicit,
                "source": str(metadata.get("source") or "extraction"),
                "effective_at": datetime.now(UTC).isoformat(),
                "provenance": provenance,
            },
        }

    # ==========================================================
    # Recall / Forget / Update
    # ==========================================================

    async def recall(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        type: MemoryType | None = None,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> MemoryRecord | None:
        if type is not None:
            return await self._registry[type].recall(
                owner_id=owner_id,
                memory_id=memory_id,
                scope_type=scope_type,
                project_id=project_id,
            )

        for service in self._registry.values():
            record = await service.recall(
                owner_id=owner_id,
                memory_id=memory_id,
                scope_type=scope_type,
                project_id=project_id,
            )

            if record is not None:
                return record

        return None

    async def forget(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        type: MemoryType | None = None,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> bool:
        if type is not None:
            deleted = await self._registry[type].forget(
                owner_id=owner_id,
                memory_id=memory_id,
                scope_type=scope_type,
                project_id=project_id,
            )
            if (
                deleted
                and type in {MemoryType.SEMANTIC, MemoryType.RESEARCH}
                and self._availability
            ):
                await self._availability.invalidate(
                    owner_id=owner_id, scope_type=scope_type, project_id=project_id
                )
            return deleted

        for memory_type, service in self._registry.items():
            if await service.forget(
                owner_id=owner_id,
                memory_id=memory_id,
                scope_type=scope_type,
                project_id=project_id,
            ):
                if memory_type in {MemoryType.SEMANTIC, MemoryType.RESEARCH} and self._availability:
                    await self._availability.invalidate(
                        owner_id=owner_id, scope_type=scope_type, project_id=project_id
                    )
                return True

        return False

    async def update_memory(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        type: MemoryType | None = None,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float | None = None,
    ) -> MemoryRecord | None:
        existing = await self.recall(
            owner_id=owner_id,
            memory_id=memory_id,
            type=type,
            scope_type=scope_type,
            project_id=project_id,
        )
        if existing is None:
            return None
        if (
            content is not None
            and content != existing.content
            and existing.type != MemoryType.SESSION
        ):
            duplicate = await self._find_exact_in_type(
                memory_type=existing.type,
                owner_id=owner_id,
                content=content,
                scope_type=scope_type,
                project_id=project_id,
            )
            if duplicate is not None and duplicate.id != memory_id:
                raise MemoryValidationError("An identical memory already exists in this scope.")

        edit_metadata = {**existing.metadata, **(metadata or {})}
        history = edit_metadata.get("_user_edit_history")
        history = list(history) if isinstance(history, list) else []
        history.append(
            {
                "edited_at": datetime.now(UTC).isoformat(),
                "previous_updated_at": existing.updated_at.isoformat(),
            }
        )
        edit_metadata.update(
            {
                "source": "manual",
                "origin": "explicit",
                "_user_edit_history": history[-10:],
            }
        )

        services = [self._registry[existing.type]]

        for service in services:
            updated = await service.update(
                owner_id=owner_id,
                memory_id=memory_id,
                scope_type=scope_type,
                project_id=project_id,
                content=content,
                metadata=edit_metadata,
                importance_score=importance_score,
            )

            if updated is not None:
                if (
                    existing.type in {MemoryType.SEMANTIC, MemoryType.RESEARCH}
                    and self._availability
                ):
                    await self._availability.invalidate(
                        owner_id=owner_id, scope_type=scope_type, project_id=project_id
                    )
                return updated

        return None

    async def move_memory(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        source_scope_type: MemoryScopeType,
        source_project_id: UUID | None,
        destination_scope_type: MemoryScopeType,
        destination_project_id: UUID | None,
    ) -> MemoryRecord | None:
        existing = await self.recall(
            owner_id=owner_id,
            memory_id=memory_id,
            scope_type=source_scope_type,
            project_id=source_project_id,
        )
        if existing is None:
            return None
        if existing.type == MemoryType.SESSION:
            raise MemoryValidationError("SESSION memory cannot be moved between scopes.")
        duplicate = await self._find_exact_in_type(
            memory_type=existing.type,
            owner_id=owner_id,
            content=existing.content,
            scope_type=destination_scope_type,
            project_id=destination_project_id,
        )
        if duplicate is not None:
            raise MemoryValidationError("An identical memory already exists in the destination.")

        moved_metadata = {
            **existing.metadata,
            "_scope_move": {
                "source_scope": source_scope_type.value,
                "source_project_id": str(source_project_id) if source_project_id else None,
                "moved_at": datetime.now(UTC).isoformat(),
                "confirmed": True,
            },
        }
        created = await self.remember(
            owner_id=owner_id,
            type=existing.type,
            content=existing.content,
            scope_type=destination_scope_type,
            project_id=destination_project_id,
            importance_score=existing.importance_score,
            metadata=moved_metadata,
        )
        if created is None:
            raise MemoryValidationError("Memory did not pass destination validation.")
        deleted = await self.forget(
            owner_id=owner_id,
            memory_id=existing.id,
            type=existing.type,
            scope_type=source_scope_type,
            project_id=source_project_id,
        )
        if not deleted:
            await self.forget(
                owner_id=owner_id,
                memory_id=created.id,
                type=created.type,
                scope_type=destination_scope_type,
                project_id=destination_project_id,
            )
            raise MemoryValidationError("Memory move could not remove the source record.")
        return created

    async def get_scope_settings(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
    ) -> tuple[bool, bool, bool]:
        if self._scope_settings is None:
            return True, True, True
        row = await self._scope_settings.get(
            owner_id=owner_id, scope_type=scope_type, project_id=project_id
        )
        return (
            (
                row.capture_enabled,
                row.retrieval_enabled,
                getattr(row, "inherit_personal_memory", True),
            )
            if row
            else (True, True, True)
        )

    async def update_scope_settings(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
        capture_enabled: bool,
        retrieval_enabled: bool,
        inherit_personal_memory: bool = True,
    ) -> tuple[bool, bool, bool]:
        if self._scope_settings is None:
            raise MemoryValidationError("Memory scope settings are unavailable.")
        row = await self._scope_settings.upsert(
            owner_id=owner_id,
            scope_type=scope_type,
            project_id=project_id,
            capture_enabled=capture_enabled,
            retrieval_enabled=retrieval_enabled,
            inherit_personal_memory=inherit_personal_memory,
        )
        return row.capture_enabled, row.retrieval_enabled, row.inherit_personal_memory

    async def _capture_enabled(
        self, owner_id: UUID, scope_type: MemoryScopeType, project_id: UUID | None
    ) -> bool:
        capture_enabled, _, _ = await self.get_scope_settings(
            owner_id=owner_id, scope_type=scope_type, project_id=project_id
        )
        return capture_enabled

    async def _retrieval_enabled(
        self, owner_id: UUID, scope_type: MemoryScopeType, project_id: UUID | None
    ) -> bool:
        _, retrieval_enabled, _ = await self.get_scope_settings(
            owner_id=owner_id, scope_type=scope_type, project_id=project_id
        )
        return retrieval_enabled

    async def _find_exact_in_type(
        self,
        *,
        memory_type: MemoryType,
        owner_id: UUID,
        content: str,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
    ) -> MemoryRecord | None:
        if memory_type == MemoryType.USER:
            return await self._user.find_exact_content(
                owner_id=owner_id,
                content=content,
                scope_type=scope_type,
                project_id=project_id,
            )
        elif memory_type == MemoryType.SEMANTIC:
            return await self._semantic.find_exact_content(
                owner_id=owner_id,
                content=content,
                scope_type=scope_type,
                project_id=project_id,
            )
        return await self._research.find_exact_content(
            owner_id=owner_id,
            content=content,
            scope_type=scope_type,
            project_id=project_id,
        )

    # ==========================================================
    # Search
    # ==========================================================

    async def search(
        self,
        request: MemorySearchRequest,
    ) -> MemorySearchResult:
        started = perf_counter()
        if not await self._retrieval_enabled(
            request.owner_id, request.scope_type, request.project_id
        ):
            result = MemorySearchResult(memories=[], latency_ms=(perf_counter() - started) * 1000)
            self._metrics.increment(metric=MEMORY_MISSES)
            return result

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
                        scope_type=request.scope_type,
                        project_id=request.project_id,
                        limit=request.top_k,
                    )
                )
                continue

            result_lists.append(
                await vector_backed_services[memory_type].search(
                    owner_id=request.owner_id,
                    scope_type=request.scope_type,
                    project_id=request.project_id,
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
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        inherit_personal_user_memory: bool = True,
        semantic_query: str | None = None,
        top_k: int = 10,
        transcript: str | None = None,
    ) -> MemoryContext:
        started = perf_counter()
        self._metrics.increment(metric=CONTEXT_REQUESTS)
        logger.info(
            "memory.context.started",
            owner_id=str(owner_id),
            session_id=str(session_id),
            query_length=len(semantic_query or ""),
        )
        if not await self._retrieval_enabled(owner_id, scope_type, project_id):
            self._metrics.increment(metric=CONTEXT_RETRIEVAL_SKIPPED)
            return MemoryContext()
        session_memories = await self._session.get_context(
            owner_id=owner_id,
            session_id=session_id,
            scope_type=scope_type,
            project_id=project_id,
            limit=top_k,
        )
        for _ in session_memories:
            self._metrics.increment(metric=SESSION_ITEMS_LOADED)

        _, _, configured_personal_inheritance = await self.get_scope_settings(
            owner_id=owner_id, scope_type=scope_type, project_id=project_id
        )
        inherit_personal = (
            scope_type == MemoryScopeType.PROJECT
            and inherit_personal_user_memory
            and configured_personal_inheritance
            and await self._retrieval_enabled(owner_id, MemoryScopeType.PERSONAL, None)
        )
        if inherit_personal:
            personal_user, project_user = await asyncio.gather(
                self._user.list_preferences(
                    owner_id=owner_id,
                    scope_type=MemoryScopeType.PERSONAL,
                    project_id=None,
                    limit=top_k,
                ),
                self._user.list_preferences(
                    owner_id=owner_id,
                    scope_type=scope_type,
                    project_id=project_id,
                    limit=top_k,
                ),
            )
            user_memories = (personal_user + project_user)[:top_k]
        else:
            user_memories = await self._user.list_preferences(
                owner_id=owner_id,
                scope_type=scope_type,
                project_id=project_id,
                limit=top_k,
            )

        semantic_memories: list[MemoryRecord] = []
        research_memories: list[MemoryRecord] = []

        if semantic_query and settings.memory_durable_retrieval_enabled:
            has_durable_memory = (
                await self._availability.has_durable_memory(
                    owner_id=owner_id, scope_type=scope_type, project_id=project_id
                )
                if self._availability is not None
                else True
            )
            if has_durable_memory:
                self._metrics.increment(metric=CONTEXT_DURABLE_AVAILABLE)
                search_started = perf_counter()
                try:
                    embedding = await self._semantic.embed_query(semantic_query)
                    if settings.memory_parallel_search_enabled:
                        self._metrics.increment(metric=PARALLEL_SEARCH)
                        results = await asyncio.gather(
                            self._semantic.search_with_embedding(
                                owner_id=owner_id,
                                scope_type=scope_type,
                                project_id=project_id,
                                embedding=embedding,
                                top_k=top_k,
                            ),
                            self._research.search_with_embedding(
                                owner_id=owner_id,
                                scope_type=scope_type,
                                project_id=project_id,
                                embedding=embedding,
                                top_k=top_k,
                            ),
                            return_exceptions=True,
                        )
                        if isinstance(results[0], list):
                            semantic_memories = results[0]
                            self._metrics.increment(metric=SEMANTIC_SEARCH)
                        else:
                            self._log_search_failure("semantic", owner_id, results[0])
                        if isinstance(results[1], list):
                            research_memories = results[1]
                            self._metrics.increment(metric=RESEARCH_SEARCH)
                        else:
                            self._log_search_failure("research", owner_id, results[1])
                    else:
                        try:
                            semantic_memories = await self._semantic.search_with_embedding(
                                owner_id=owner_id,
                                scope_type=scope_type,
                                project_id=project_id,
                                embedding=embedding,
                                top_k=top_k,
                            )
                            self._metrics.increment(metric=SEMANTIC_SEARCH)
                        except Exception as exc:
                            self._log_search_failure("semantic", owner_id, exc)
                        try:
                            research_memories = await self._research.search_with_embedding(
                                owner_id=owner_id,
                                scope_type=scope_type,
                                project_id=project_id,
                                embedding=embedding,
                                top_k=top_k,
                            )
                            self._metrics.increment(metric=RESEARCH_SEARCH)
                        except Exception as exc:
                            self._log_search_failure("research", owner_id, exc)
                except Exception as exc:
                    logger.warning(
                        "memory.retrieval.embedding_failed",
                        owner_id=str(owner_id),
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                finally:
                    self._metrics.record_duration(
                        operation=DURABLE_SEARCH_LATENCY,
                        duration_ms=(perf_counter() - search_started) * 1000,
                    )
            else:
                self._metrics.increment(metric=CONTEXT_DURABLE_EMPTY)
                self._metrics.increment(metric=CONTEXT_RETRIEVAL_SKIPPED)
                logger.info(
                    "memory.context.skipped_durable_retrieval",
                    owner_id=str(owner_id),
                    session_id=str(session_id),
                )

        deduplicated_session = self._deduplicate_session_history(session_memories, transcript)
        for _ in range(len(session_memories) - len(deduplicated_session)):
            self._metrics.increment(metric=SESSION_DUPLICATES_REMOVED)
        context = MemoryContext(
            session_memories=deduplicated_session,
            user_memories=user_memories,
            semantic_memories=semantic_memories,
            research_memories=research_memories,
        )

        await self._persist_context_artifact(
            owner_id=owner_id,
            session_id=session_id,
            scope_type=scope_type,
            project_id=project_id,
            context=context,
        )

        latency_ms = (perf_counter() - started) * 1000
        self._metrics.record_duration(operation=CONTEXT_LATENCY, duration_ms=latency_ms)
        logger.info(
            "memory.context.completed",
            owner_id=str(owner_id),
            session_id=str(session_id),
            session_result_count=len(context.session_memories),
            user_result_count=len(context.user_memories),
            semantic_result_count=len(context.semantic_memories),
            research_result_count=len(context.research_memories),
            latency_ms=latency_ms,
        )
        return context

    async def get_latest_session_state(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        kind: str,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        limit: int = 50,
    ) -> MemoryRecord | None:
        """The most recent SESSION record tagged `metadata["kind"] == kind`
        -- used to upsert a single evolving "current state" slot per
        session (see `SessionStateUpdaterService`) rather than growing an
        unbounded pile of state snapshots. Bypasses `get_context()`'s
        semantic-search/dedup machinery, both irrelevant here: this is a
        plain tag lookup over the session's own recency window.
        `SessionMemoryService.get_context()` returns oldest-first, so the
        last match in the list is the most recent."""

        records = await self._session.get_context(
            owner_id=owner_id,
            session_id=session_id,
            scope_type=scope_type,
            project_id=project_id,
            limit=limit,
        )
        matches = [record for record in records if record.metadata.get("kind") == kind]
        return matches[-1] if matches else None

    @staticmethod
    def _deduplicate_session_history(
        memories: list[MemoryRecord],
        transcript: str | None,
    ) -> list[MemoryRecord]:
        if not settings.memory_context_deduplication_enabled or not transcript:
            return memories
        normalized_transcript = " ".join(transcript.lower().split())
        return [
            memory
            for memory in memories
            if not (
                # Transitional raw entries are redundant when their source
                # turn is already present in canonical persisted history.
                (
                    memory.content.startswith("Q: ")
                    and " ".join(memory.content.lower().split()) in normalized_transcript
                )
                or (
                    len(" ".join(memory.content.split())) >= 32
                    and " ".join(memory.content.lower().split()) in normalized_transcript
                )
            )
        ]

    @staticmethod
    def _log_search_failure(category: str, owner_id: UUID, error: object) -> None:
        exc = error if isinstance(error, Exception) else Exception(str(error))
        logger.warning(
            f"memory.{category}_search.failed",
            owner_id=str(owner_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )

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
                scope_type=request.scope_type,
                project_id=request.project_id,
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
        scope_type: MemoryScopeType,
        project_id: UUID | None,
        context: MemoryContext,
    ) -> None:
        if self._artifact_writer is None:
            return

        try:
            artifact = MemoryArtifactBuilder().build_context(
                owner_id=owner_id,
                session_id=session_id,
                scope_type=scope_type,
                project_id=project_id,
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
