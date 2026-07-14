from app.ai.knowledge.context.models import (
    ContextChunk,
)


class ContextOrderingService:
    def order(
        self,
        chunks: list[ContextChunk],
    ) -> list[ContextChunk]:

        return sorted(
            chunks,
            key=lambda c: (
                c.score,
                -c.chunk_index,
            ),
            reverse=True,
        )
