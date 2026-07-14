from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ==========================================================
# Base Requests
# ==========================================================


class BaseRetrieveRequest(BaseModel):
    """
    Base retrieval request.
    """

    query: str = Field(
        min_length=1,
        description="Search query.",
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of chunks to return.",
    )

    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata filters.",
    )


# ==========================================================
# Dense Retrieval
# ==========================================================


class DenseRetrieveRequest(
    BaseRetrieveRequest,
):
    """
    Dense retrieval request.
    """


# ==========================================================
# Sparse Retrieval
# ==========================================================


class SparseRetrieveRequest(
    BaseRetrieveRequest,
):
    """
    Sparse retrieval request.
    """


# ==========================================================
# Hybrid Retrieval
# ==========================================================


class HybridRetrieveRequest(
    BaseRetrieveRequest,
):
    """
    Hybrid retrieval request.
    """

    rerank: bool = Field(
        default=True,
        description=("Apply reranking after hybrid fusion."),
    )
    # reranking_provider: str | None = None

    # candidate_multiplier: int = Field(
    #     default=5,
    #     ge=1,
    #     le=20,
    # )


# ==========================================================
# Responses
# ==========================================================


class RetrievedChunkResponse(BaseModel):
    """
    Retrieved chunk response.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    chunk_id: uuid.UUID

    document_id: uuid.UUID

    filename: str

    chunk_index: int

    content: str

    score: float


class RetrieveResponse(BaseModel):
    """
    Retrieval response.
    """

    query: str

    total_chunks: int

    duration_ms: float

    chunks: list[RetrievedChunkResponse]
