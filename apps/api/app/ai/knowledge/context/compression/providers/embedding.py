from __future__ import annotations

from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.compression.interfaces import (
    CompressionProvider,
)
from app.ai.knowledge.context.compression.models import (
    CompressionRequest,
    CompressionResult,
    CompressionStatistics,
)
from app.ai.shared.local_embeddings import (
    get_local_embedding_model,
)
from sklearn.metrics.pairwise import (
    cosine_similarity,
)


class EmbeddingCompressionProvider(
    CompressionProvider,
):
    """
    Remove semantically redundant chunks.
    """

    DEFAULT_THRESHOLD = 0.95

    def __init__(
        self,
        similarity_threshold: float = DEFAULT_THRESHOLD,
    ) -> None:

        self._threshold = similarity_threshold

        self._model = get_local_embedding_model()

    async def compress(
        self,
        request: CompressionRequest,
    ) -> CompressionResult:

        chunks = request.chunks

        if len(chunks) <= 1:
            return CompressionResult(
                strategy=(CompressionStrategy.EMBEDDING_REDUNDANCY),
                chunks=chunks,
                statistics=(
                    CompressionStatistics(
                        original_chunks=len(chunks),
                        compressed_chunks=len(chunks),
                        removed_chunks=0,
                    )
                ),
            )

        texts = [chunk.content for chunk in chunks]

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            convert_to_tensor=False,
        )

        similarity_matrix = cosine_similarity(
            embeddings,
        )

        selected = []

        removed = set()

        for i in range(len(chunks)):
            if i in removed:
                continue

            selected.append(chunks[i])

            for j in range(
                i + 1,
                len(chunks),
            ):
                similarity = similarity_matrix[i][j]

                if similarity >= self._threshold:
                    removed.add(j)

        return CompressionResult(
            strategy=(CompressionStrategy.EMBEDDING_REDUNDANCY),
            chunks=selected,
            statistics=(
                CompressionStatistics(
                    original_chunks=len(chunks),
                    compressed_chunks=len(selected),
                    removed_chunks=len(removed),
                )
            ),
        )
