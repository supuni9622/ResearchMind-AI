from __future__ import annotations

from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class Citation(
    BaseModel,
):
    """
    Canonical citation object.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    citation_id: str

    filename: str

    document_id: UUID

    page_numbers: list[int] = Field(
        default_factory=list,
    )

    heading: str | None = None

    heading_path: list[str] = Field(
        default_factory=list,
    )

    chunk_ids: list[UUID] = Field(
        default_factory=list,
    )


class CitationResult(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    citations: list[Citation]
