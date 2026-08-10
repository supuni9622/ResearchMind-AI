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

    # Defaulted, not required: `ResearchSession.citations` persists this
    # model as JSONB and replays it via `Citation.model_validate()`
    # (`execution.py::_session_response`) -- rows written before this field
    # existed have no `score` key, and a required field would break replay
    # of that historical data.
    score: float = 0.0

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
