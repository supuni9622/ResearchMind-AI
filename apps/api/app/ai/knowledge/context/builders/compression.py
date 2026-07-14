from app.ai.knowledge.context.models import (
    ContextChunk,
)


class CompressionService:
    """
    Initial implementation.

    Future:

    ContextualCompressionRetriever
    LLM compression
    Token aware compression
    """

    def compress(
        self,
        chunks: list[ContextChunk],
    ) -> list[ContextChunk]:

        return chunks
