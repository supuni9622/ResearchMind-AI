from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.ai.memory.models import MemorySearchRequest
from app.ai.memory.services.memory_service import MemoryService
from app.auth.dependencies import get_current_user
from app.dependencies.memory import get_memory_service
from app.exceptions.base import NotFoundException
from app.models.user import User
from app.schemas.memory import (
    MemoryContextResponse,
    MemoryRecordResponse,
    MemoryRememberRequest,
    MemorySearchApiRequest,
    MemorySearchResponse,
    MemoryUpdateRequest,
)

router = APIRouter(
    prefix="/memory",
    tags=["Memory"],
)


@router.post(
    "",
    response_model=MemoryRecordResponse | None,
    summary="Remember a piece of information",
)
async def remember(
    payload: MemoryRememberRequest,
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryRecordResponse | None:
    """
    Returns `null` when the memory's importance score falls below the
    configured threshold -- it was intentionally not persisted (PRD
    §16), not an error.
    """

    record = await memory_service.remember(
        owner_id=current_user.id,
        type=payload.type,
        content=payload.content,
        session_id=payload.session_id,
        metadata=payload.metadata,
        importance_score=payload.importance_score,
    )

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
) -> MemorySearchResponse:
    result = await memory_service.search(
        MemorySearchRequest(
            query=payload.query,
            owner_id=current_user.id,
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
    current_user: User = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryContextResponse:
    context = await memory_service.get_context(
        owner_id=current_user.id,
        session_id=session_id,
        semantic_query=semantic_query,
        top_k=top_k,
    )

    return MemoryContextResponse(
        session_memories=[
            MemoryRecordResponse.model_validate(m.model_dump()) for m in context.session_memories
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
) -> MemoryRecordResponse:
    record = await memory_service.recall(owner_id=current_user.id, memory_id=memory_id)

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
) -> MemoryRecordResponse:
    record = await memory_service.update_memory(
        owner_id=current_user.id,
        memory_id=memory_id,
        type=payload.type,
        content=payload.content,
        metadata=payload.metadata,
        importance_score=payload.importance_score,
    )

    if record is None:
        raise NotFoundException(message=f"Memory '{memory_id}' was not found.")

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
) -> None:
    deleted = await memory_service.forget(owner_id=current_user.id, memory_id=memory_id)

    if not deleted:
        raise NotFoundException(message=f"Memory '{memory_id}' was not found.")
