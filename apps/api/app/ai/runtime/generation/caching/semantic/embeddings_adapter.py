"""
Thin `langchain_core.embeddings.Embeddings` adapter over the OpenAI
embeddings client, so `RedisSemanticCache` (which requires a LangChain
`Embeddings` instance) can embed prompts without pulling in the
Knowledge Platform's document-oriented `EmbeddingProvider` interface
(that one embeds `ChunkArtifact`s, not raw strings).

Only the sync methods are implemented. `Embeddings.aembed_query` /
`aembed_documents` already default to delegating to these via a
thread-pool executor, so `RedisSemanticCache`'s async lookup/update
path works correctly without any async override here.
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from openai import OpenAI


class OpenAISemanticCacheEmbeddings(
    Embeddings,
):
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str,
    ) -> None:
        self._client = client
        self._model = model

    def embed_query(
        self,
        text: str,
    ) -> list[float]:

        response = self._client.embeddings.create(
            model=self._model,
            input=[text],
        )

        return [float(value) for value in response.data[0].embedding]

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
        )

        return [[float(value) for value in item.embedding] for item in response.data]
