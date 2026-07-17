"""
Research Service internal models (research_api_prd.md §9/§10).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.knowledge.context.citations.models import Citation


class ResearchSource(BaseModel):
    """
    A single retrieved-and-cited source (research_api_prd.md §9).

    Built from a `ContextChunk` (post context-building enrichment) rather
    than the raw `RetrievedChunk` -- `page` only becomes available after
    parent expansion fills in `page_numbers`.
    """

    model_config = ConfigDict(extra="forbid")

    document_id: UUID

    filename: str

    chunk_id: UUID

    score: float

    page: int | None = None


class ResearchOutcome(BaseModel):
    """
    Result of a completed (non-streaming) research run.

    Bundles everything `ResearchService.research()` produces so the
    route can build a `ResearchResponse` without re-deriving anything --
    session/artifact persistence has already happened by the time this
    is returned.
    """

    model_config = ConfigDict(extra="forbid")

    research_id: UUID

    query: str

    answer: str

    citations: list[Citation]

    sources: list[ResearchSource]

    duration_ms: float
