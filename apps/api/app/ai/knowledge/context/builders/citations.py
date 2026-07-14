from app.ai.knowledge.context.models import (
    ContextChunk,
)


class CitationService:
    def build(
        self,
        chunks: list[ContextChunk],
    ) -> str:

        sections = []

        for i, chunk in enumerate(chunks):
            sections.append(
                f"""
            [Source {i + 1}]
            Document: {chunk.filename}
            Chunk: {chunk.chunk_index}

            {chunk.content}
            """
            )

        return "\n".join(sections)
