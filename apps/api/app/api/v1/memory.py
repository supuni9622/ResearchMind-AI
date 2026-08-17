from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.ai.memory.create import get_memory_metrics
from app.ai.memory.enums import MemoryScopeType
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
from app.exceptions.base import NotFoundException, RateLimitExceededException
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.rate_limiting import ValkeyRateLimiter
from app.models.user import User
from app.schemas.memory import (
    MemoryContextResponse,
    MemoryListResponse,
    MemoryRecordResponse,
    MemoryRememberRequest,
    MemorySearchApiRequest,
    MemorySearchResponse,
    MemoryUpdateRequest,
)
from app.services.project_authorization import ProjectAuthorizationService

router = APIRouter(
    prefix="/memory",
    tags=["Memory"],
)


@router.get(
    "",
    response_model=MemoryListResponse,
    summary="List the current user's profile memories",
)
async def list_user_memories(
    search: str | None = Query(default=None, min_length=1, max_length=200),
    source: str | None = Query(default=None, min_length=1, max_length=50),
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
    memories, total = await memory_service.list_user_memories(
        owner_id=current_user.id,
        scope_type=scope_type,
        project_id=project_id,
        search=search,
        source=source,
        limit=limit,
        offset=offset,
    )
    return MemoryListResponse(
        memories=[MemoryRecordResponse.model_validate(memory.model_dump()) for memory in memories],
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
            metadata=payload.metadata,
            importance_score=payload.importance_score,
        )
    except Exception:
        _record_mutation(metrics, operation="create", outcome="failed")
        raise
    _record_mutation(metrics, operation="create", outcome="accepted")

    return MemoryRecordResponse.model_validate(record.model_dump()) if record else None


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
        memories=[MemoryRecordResponse.model_validate(m.model_dump()) for m in result.memories],
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
        session_memories=[
            MemoryRecordResponse.model_validate(m.model_dump()) for m in context.session_memories
        ],
        user_memories=[
            MemoryRecordResponse.model_validate(m.model_dump()) for m in context.user_memories
        ],
        semantic_memories=[
            MemoryRecordResponse.model_validate(m.model_dump()) for m in context.semantic_memories
        ],
        research_memories=[
            MemoryRecordResponse.model_validate(m.model_dump()) for m in context.research_memories
        ],
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

    return MemoryRecordResponse.model_validate(record.model_dump())


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
    except Exception:
        _record_mutation(metrics, operation="update", outcome="failed")
        raise

    if record is None:
        _record_mutation(metrics, operation="update", outcome="failed")
        raise NotFoundException(message=f"Memory '{memory_id}' was not found.")

    _record_mutation(metrics, operation="update", outcome="accepted")
    return MemoryRecordResponse.model_validate(record.model_dump())


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
