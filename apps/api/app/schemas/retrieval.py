from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class RetrieveRequest(BaseModel):
    """
    Retrieval request.
    """

    query: str = Field(
        min_length=1,
        description="Search query.",
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
    )


class RetrievedChunkResponse(BaseModel):
    """
    Retrieved chunk.
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
