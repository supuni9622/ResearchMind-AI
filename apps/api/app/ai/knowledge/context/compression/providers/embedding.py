from app.ai.knowledge.context.compression.interfaces import (
    CompressionProvider,
)
from app.ai.knowledge.context.compression.models import (
    CompressionRequest,
    CompressionResult,
)


class EmbeddingCompressionProvider(
    CompressionProvider,
):
    async def compress(
        self,
        request: CompressionRequest,
    ) -> CompressionResult:

        raise NotImplementedError
