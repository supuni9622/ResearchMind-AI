from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.ai.memory.create import get_memory_metrics
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.exceptions import MemoryValidationError
from app.ai.memory.models import MemorySearchRequest
from app.ai.memory.observability.metrics import (
    MEMORY_MUTATION_ACCEPTED,
    MEMORY_MUTATION_FAILED,
    MEMORY_MUTATION_REJECTED,
)
from app.ai.memory.services.memory_service import MemoryService
from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.dependencies.memory import get_memory_service
from app.dependencies.project import get_project_authorization_service
from app.dependencies.rate_limiting import enforce_rate_limit, get_rate_limiter
from app.exceptions.base import NotFoundException, RateLimitExceededException, ValidationException
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.rate_limiting import ValkeyRateLimiter
from app.models.user import User
from app.schemas.memory import (
    MemoryContextResponse,
    MemoryListResponse,
    MemoryMoveRequest,
    MemoryOrigin,
    MemoryProjectResponse,
    MemoryRecordResponse,
    MemoryRememberRequest,
    MemoryScopeSettingsResponse,
    MemoryScopeSettingsUpdate,
    MemorySearchApiRequest,
    MemorySearchResponse,
    MemoryUpdateRequest,
)
from app.services.project_authorization import ProjectAuthorizationService

router = APIRouter(
    prefix="/memory",
    tags=["Memory"],
)


@router.get("/projects", response_model=list[MemoryProjectResponse])
async def list_memory_projects(
    current_user: User = Depends(get_current_user),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> list[MemoryProjectResponse]:
    projects = await project_authorization.list_accessible_projects(user_id=current_user.id)
    return [
        MemoryProjectResponse(id=project.id, name=project.name, role=role)
        for project, role in projects
    ]


@router.get(
    "",
    response_model=MemoryListResponse,
    summary="List the current user's profile memories",
)
async def list_user_memories(
    search: str | None = Query(default=None, min_length=1, max_length=200),
    source: str | None = Query(default=None, min_length=1, max_length=50),
    types: list[MemoryType] | None = Query(default=None, alias="type"),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    updated_from: datetime | None = Query(default=None),
    updated_to: datetime | None = Query(default=None),
    origin: MemoryOrigin | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    scope_type: MemoryScopeType = Query(default=MemoryScopeType.PERSONAL),
    project_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> MemoryListResponse:
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id, scope_type=scope_type, project_id=project_id
    )
    if types and MemoryType.SESSION in types:
        raise ValidationException(message="SESSION memory is not globally enumerable.")
    if created_from and created_to and created_from > created_to:
        raise ValidationException(message="created_from must be before created_to.")
    if updated_from and updated_to and updated_from > updated_to:
        raise ValidationException(message="updated_from must be before updated_to.")
    memories, total = await memory_service.list_memories(
        owner_id=current_user.id,
        memory_types=types,
        scope_type=scope_type,
        project_id=project_id,
        search=search,
        source=source,
        created_from=created_from,
        created_to=created_to,
        updated_from=updated_from,
        updated_to=updated_to,
        origin=origin.value if origin else None,
        limit=limit,
        offset=offset,
    )
    return MemoryListResponse(
        memories=[MemoryRecordResponse.from_record(memory) for memory in memories],
        total=total,
        limit=limit,
        offset=offset,
    )


async def _check_memory_mutation_rate_limit(
    *,
    rate_limiter: ValkeyRateLimiter,
    metrics: MetricsRecorder,
    owner_id: UUID,
    operation: str,
) -> None:
    destructive = operation == "delete"
    try:
        await enforce_rate_limit(
            rate_limiter,
            scope="memory_delete" if destructive else "memory_write",
            owner_id=owner_id,
            limit=(
                settings.memory_delete_rate_limit_requests
                if destructive
                else settings.memory_write_rate_limit_requests
            ),
            window_seconds=(
                settings.memory_delete_rate_limit_window_seconds
                if destructive
                else settings.memory_write_rate_limit_window_seconds
            ),
        )
    except RateLimitExceededException:
        metrics.increment(metric=MEMORY_MUTATION_REJECTED, labels={"operation": operation})
        raise


def _record_mutation(metrics: MetricsRecorder, *, operation: str, outcome: str) -> None:
    metric = MEMORY_MUTATION_ACCEPTED if outcome == "accepted" else MEMORY_MUTATION_FAILED
    metrics.increment(metric=metric, labels={"operation": operation})


@router.post(
    "",
    response_model=MemoryRecordResponse | None,
    summary="Remember a piece of information",
)
async def remember(
    payload: MemoryRememberRequest,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    metrics: MetricsRecorder = Depends(get_memory_metrics),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> MemoryRecordResponse | None:
    """
    Returns `null` when the memory's importance score falls below the
    configured threshold -- it was intentionally not persisted (PRD
    §16), not an error.
    """

    await project_authorization.authorize_memory_scope(
        user_id=current_user.id,
        scope_type=payload.scope_type,
        project_id=payload.project_id,
    )
    await _check_memory_mutation_rate_limit(
        rate_limiter=rate_limiter,
        metrics=metrics,
        owner_id=current_user.id,
        operation="create",
    )
    try:
        record = await memory_service.remember(
            owner_id=current_user.id,
            type=payload.type,
            scope_type=payload.scope_type,
            project_id=payload.project_id,
            content=payload.content,
            session_id=payload.session_id,
            metadata={**payload.metadata, "source": "manual", "origin": "explicit"},
            importance_score=payload.importance_score,
        )
    except MemoryValidationError as exc:
        _record_mutation(metrics, operation="create", outcome="failed")
        raise ValidationException(message=str(exc)) from exc
    except Exception:
        _record_mutation(metrics, operation="create", outcome="failed")
        raise
    _record_mutation(metrics, operation="create", outcome="accepted")

    return MemoryRecordResponse.from_record(record) if record else None


@router.post(
    "/search",
    response_model=MemorySearchResponse,
    summary="Semantically search memories",
)
async def search_memories(
    payload: MemorySearchApiRequest,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> MemorySearchResponse:
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id,
        scope_type=payload.scope_type,
        project_id=payload.project_id,
    )
    result = await memory_service.search(
        MemorySearchRequest(
            query=payload.query,
            owner_id=current_user.id,
            scope_type=payload.scope_type,
            project_id=payload.project_id,
            memory_types=payload.memory_types,
            top_k=payload.top_k,
        )
    )

    return MemorySearchResponse(
        memories=[MemoryRecordResponse.from_record(m) for m in result.memories],
        latency_ms=result.latency_ms,
    )


@router.get(
    "/context",
    response_model=MemoryContextResponse,
    summary="Assemble the memory context for a session",
)
async def get_memory_context(
    session_id: UUID = Query(...),
    semantic_query: str | None = Query(default=None),
    top_k: int = Query(default=10, ge=1, le=100),
    scope_type: MemoryScopeType = Query(default=MemoryScopeType.PERSONAL),
    project_id: UUID | None = Query(default=None),
    inherit_personal_user_memory: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> MemoryContextResponse:
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id, scope_type=scope_type, project_id=project_id
    )
    context = await memory_service.get_context(
        owner_id=current_user.id,
        session_id=session_id,
        scope_type=scope_type,
        project_id=project_id,
        inherit_personal_user_memory=inherit_personal_user_memory,
        semantic_query=semantic_query,
        top_k=top_k,
    )

    return MemoryContextResponse(
        session_memories=[MemoryRecordResponse.from_record(m) for m in context.session_memories],
        user_memories=[MemoryRecordResponse.from_record(m) for m in context.user_memories],
        semantic_memories=[MemoryRecordResponse.from_record(m) for m in context.semantic_memories],
        research_memories=[MemoryRecordResponse.from_record(m) for m in context.research_memories],
    )


@router.get("/settings", response_model=MemoryScopeSettingsResponse)
async def get_memory_scope_settings(
    scope_type: MemoryScopeType = Query(default=MemoryScopeType.PERSONAL),
    project_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> MemoryScopeSettingsResponse:
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id, scope_type=scope_type, project_id=project_id
    )
    (
        capture_enabled,
        retrieval_enabled,
        inherit_personal_memory,
    ) = await memory_service.get_scope_settings(
        owner_id=current_user.id, scope_type=scope_type, project_id=project_id
    )
    return MemoryScopeSettingsResponse(
        scope_type=scope_type,
        project_id=project_id,
        capture_enabled=capture_enabled,
        retrieval_enabled=retrieval_enabled,
        inherit_personal_memory=inherit_personal_memory,
    )


@router.put("/settings", response_model=MemoryScopeSettingsResponse)
async def update_memory_scope_settings(
    payload: MemoryScopeSettingsUpdate,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    metrics: MetricsRecorder = Depends(get_memory_metrics),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> MemoryScopeSettingsResponse:
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id, scope_type=payload.scope_type, project_id=payload.project_id
    )
    await _check_memory_mutation_rate_limit(
        rate_limiter=rate_limiter,
        metrics=metrics,
        owner_id=current_user.id,
        operation="settings",
    )
    (
        capture_enabled,
        retrieval_enabled,
        inherit_personal_memory,
    ) = await memory_service.update_scope_settings(
        owner_id=current_user.id,
        scope_type=payload.scope_type,
        project_id=payload.project_id,
        capture_enabled=payload.capture_enabled,
        retrieval_enabled=payload.retrieval_enabled,
        inherit_personal_memory=payload.inherit_personal_memory,
    )
    _record_mutation(metrics, operation="settings", outcome="accepted")
    return MemoryScopeSettingsResponse(
        scope_type=payload.scope_type,
        project_id=payload.project_id,
        capture_enabled=capture_enabled,
        retrieval_enabled=retrieval_enabled,
        inherit_personal_memory=inherit_personal_memory,
    )


@router.get(
    "/{memory_id}",
    response_model=MemoryRecordResponse,
    summary="Recall a memory by id",
)
async def recall_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    scope_type: MemoryScopeType = Query(default=MemoryScopeType.PERSONAL),
    project_id: UUID | None = Query(default=None),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> MemoryRecordResponse:
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id, scope_type=scope_type, project_id=project_id
    )
    record = await memory_service.recall(
        owner_id=current_user.id,
        memory_id=memory_id,
        scope_type=scope_type,
        project_id=project_id,
    )

    if record is None:
        raise NotFoundException(message=f"Memory '{memory_id}' was not found.")

    return MemoryRecordResponse.from_record(record)


@router.put(
    "/{memory_id}",
    response_model=MemoryRecordResponse,
    summary="Update a memory",
)
async def update_memory(
    memory_id: UUID,
    payload: MemoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    metrics: MetricsRecorder = Depends(get_memory_metrics),
    scope_type: MemoryScopeType = Query(default=MemoryScopeType.PERSONAL),
    project_id: UUID | None = Query(default=None),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> MemoryRecordResponse:
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id, scope_type=scope_type, project_id=project_id
    )
    await _check_memory_mutation_rate_limit(
        rate_limiter=rate_limiter,
        metrics=metrics,
        owner_id=current_user.id,
        operation="update",
    )
    try:
        record = await memory_service.update_memory(
            owner_id=current_user.id,
            memory_id=memory_id,
            type=payload.type,
            scope_type=scope_type,
            project_id=project_id,
            content=payload.content,
            metadata=payload.metadata,
            importance_score=payload.importance_score,
        )
    except MemoryValidationError as exc:
        _record_mutation(metrics, operation="update", outcome="failed")
        raise ValidationException(message=str(exc)) from exc
    except Exception:
        _record_mutation(metrics, operation="update", outcome="failed")
        raise

    if record is None:
        _record_mutation(metrics, operation="update", outcome="failed")
        raise NotFoundException(message=f"Memory '{memory_id}' was not found.")

    _record_mutation(metrics, operation="update", outcome="accepted")
    return MemoryRecordResponse.from_record(record)


@router.post("/{memory_id}/move", response_model=MemoryRecordResponse)
async def move_memory(
    memory_id: UUID,
    payload: MemoryMoveRequest,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    metrics: MetricsRecorder = Depends(get_memory_metrics),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> MemoryRecordResponse:
    if not payload.confirmed:
        raise ValidationException(message="Memory move requires explicit confirmation.")
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id,
        scope_type=payload.source_scope_type,
        project_id=payload.source_project_id,
    )
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id,
        scope_type=payload.scope_type,
        project_id=payload.project_id,
    )
    await _check_memory_mutation_rate_limit(
        rate_limiter=rate_limiter,
        metrics=metrics,
        owner_id=current_user.id,
        operation="move",
    )
    try:
        record = await memory_service.move_memory(
            owner_id=current_user.id,
            memory_id=memory_id,
            source_scope_type=payload.source_scope_type,
            source_project_id=payload.source_project_id,
            destination_scope_type=payload.scope_type,
            destination_project_id=payload.project_id,
        )
    except MemoryValidationError as exc:
        _record_mutation(metrics, operation="move", outcome="failed")
        raise ValidationException(message=str(exc)) from exc
    if record is None:
        _record_mutation(metrics, operation="move", outcome="failed")
        raise NotFoundException(message=f"Memory '{memory_id}' was not found.")
    _record_mutation(metrics, operation="move", outcome="accepted")
    return MemoryRecordResponse.from_record(record)


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Forget a memory",
)
async def forget_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    metrics: MetricsRecorder = Depends(get_memory_metrics),
    scope_type: MemoryScopeType = Query(default=MemoryScopeType.PERSONAL),
    project_id: UUID | None = Query(default=None),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
) -> None:
    await project_authorization.authorize_memory_scope(
        user_id=current_user.id, scope_type=scope_type, project_id=project_id
    )
    await _check_memory_mutation_rate_limit(
        rate_limiter=rate_limiter,
        metrics=metrics,
        owner_id=current_user.id,
        operation="delete",
    )
    try:
        deleted = await memory_service.forget(
            owner_id=current_user.id,
            memory_id=memory_id,
            scope_type=scope_type,
            project_id=project_id,
        )
    except Exception:
        _record_mutation(metrics, operation="delete", outcome="failed")
        raise

    if not deleted:
        _record_mutation(metrics, operation="delete", outcome="failed")
        raise NotFoundException(message=f"Memory '{memory_id}' was not found.")
    _record_mutation(metrics, operation="delete", outcome="accepted")
