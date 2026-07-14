from __future__ import annotations

from app.ai.knowledge.context.citations.interfaces import (
    CitationServiceInterface,
)
from app.ai.knowledge.context.citations.models import (
    Citation,
    CitationResult,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
)


class CitationService(
    CitationServiceInterface,
):
    """
    Builds canonical citations.
    """

    async def build(
        self,
        chunks: list[ContextChunk],
    ) -> CitationResult:

        citations = []

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):
            citation_id = f"S{index}"

            chunk.citation_id = citation_id

            citation = Citation(
                citation_id=(citation_id),
                filename=(chunk.filename),
                document_id=(chunk.document_id),
                page_numbers=(chunk.page_numbers),
                heading=(chunk.heading),
                heading_path=(chunk.heading_path),
                chunk_ids=(chunk.merged_chunk_ids or [chunk.chunk_id]),
            )

            citations.append(citation)

        return CitationResult(
            citations=citations,
        )
