from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
)

from app.ai.knowledge.retrieval.enums import (
    RetrievalProvider,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalQuery,
)
from app.ai.knowledge.retrieval.service import (
    RetrievalService,
)
from app.auth.dependencies import (
    get_current_user,
)
from app.dependencies.retrieval import (
    get_retrieval_service,
)
from app.models.user import User
from app.schemas.retrieval import (
    DenseRetrieveRequest,
    HybridRetrieveRequest,
    RetrievedChunkResponse,
    RetrieveResponse,
    SparseRetrieveRequest,
)


def _scoped_owner_id(
    current_user: User,
) -> str:
    """
    owner_id always comes from the authenticated user, never from the
    request body -- otherwise a caller could pass another user's
    owner_id and read their documents. `RetrievalQuery.owner_id` is a
    required field, so it must always be threaded through explicitly.
    """

    return str(current_user.id)


router = APIRouter(
    prefix="/retrieve",
    tags=["Retrieval"],
)


@router.post(
    "",
    response_model=RetrieveResponse,
)
async def retrieve(
    request: DenseRetrieveRequest,
    current_user: User = Depends(get_current_user),
    retrieval_service: RetrievalService = Depends(
        get_retrieval_service,
    ),
) -> RetrieveResponse:
    """
    Retrieve relevant chunks from knowledge base.
    """

    result = await retrieval_service.search(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            owner_id=_scoped_owner_id(current_user),
        ),
    )

    assert result.statistics is not None

    return RetrieveResponse(
        query=result.query.query,
        total_chunks=len(
            result.chunks,
        ),
        duration_ms=result.statistics.duration_ms,
        chunks=[
            RetrievedChunkResponse(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=chunk.score,
            )
            for chunk in result.chunks
        ],
    )


@router.post(
    "/sparse",
    response_model=RetrieveResponse,
)
async def retrieve_sparse(
    request: SparseRetrieveRequest,
    current_user: User = Depends(get_current_user),
    retrieval_service: RetrievalService = Depends(
        get_retrieval_service,
    ),
) -> RetrieveResponse:
    """
    Sparse retrieval using SPLADE.
    """

    result = await retrieval_service.search_sparse(
        provider=(RetrievalProvider.QDRANT),
        query=RetrievalQuery(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            owner_id=_scoped_owner_id(current_user),
        ),
    )

    assert result.statistics is not None

    return RetrieveResponse(
        query=result.query.query,
        total_chunks=len(
            result.chunks,
        ),
        duration_ms=result.statistics.duration_ms,
        chunks=[
            RetrievedChunkResponse(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=chunk.score,
            )
            for chunk in result.chunks
        ],
    )


@router.post(
    "/hybrid",
    response_model=RetrieveResponse,
)
async def retrieve_hybrid(
    request: HybridRetrieveRequest,
    current_user: User = Depends(get_current_user),
    retrieval_service: RetrievalService = Depends(
        get_retrieval_service,
    ),
) -> RetrieveResponse:
    """
    Hybrid retrieval using:

    Dense Search
            +
    Sparse Search
            ↓
    Reciprocal Rank Fusion (RRF)
    """

    result = await retrieval_service.search_hybrid(
        provider=RetrievalProvider.QDRANT,
        query=RetrievalQuery(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            owner_id=_scoped_owner_id(current_user),
        ),
    )

    assert result.statistics is not None

    return RetrieveResponse(
        query=result.query.query,
        total_chunks=len(
            result.chunks,
        ),
        duration_ms=(result.statistics.duration_ms),
        chunks=[
            RetrievedChunkResponse(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=chunk.score,
            )
            for chunk in result.chunks
        ],
    )
