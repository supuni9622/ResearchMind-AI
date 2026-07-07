"""
Unit tests for SentenceTransformerEmbeddingProvider.

Covers:
- Provider and model identifiers
- Lazy, cached construction of the SentenceTransformer model
- Conversion of encoded vectors into canonical Embedding models

Batching behavior is covered separately in test_batching.py.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import numpy as np
from app.ai.knowledge.chunking.artifacts.models import (
    ChunkArtifact,
    ChunkArtifactDocument,
    ChunkArtifactStatistics,
    ChunkArtifactStrategy,
)
from app.ai.knowledge.chunking.enums import ChunkContentType, ChunkingStrategy
from app.ai.knowledge.chunking.models import (
    Chunk,
    ChunkContent,
    ChunkExperiment,
    ChunkProvenance,
    ChunkStatistics,
    ChunkStructure,
)
from app.ai.knowledge.embeddings.config import SentenceTransformerEmbeddingConfig
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.providers.sentence_transformers import (
    SentenceTransformerEmbeddingProvider,
)

_DOCUMENT_ID = uuid.uuid4()


def _make_chunk(text: str, index: int = 0) -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        index=index,
        total_chunks=1,
        content=ChunkContent(text=text, content_type=ChunkContentType.TEXT),
        structure=ChunkStructure(),
        statistics=ChunkStatistics(character_count=len(text)),
        provenance=ChunkProvenance(
            document_id=_DOCUMENT_ID,
            filename="test.pdf",
            parser="docling",
        ),
        experiment=ChunkExperiment(
            strategy=ChunkingStrategy.FIXED,
            configuration_fingerprint="fingerprint",
        ),
    )


def _make_chunk_artifact(chunks: list[Chunk]) -> ChunkArtifact:
    return ChunkArtifact(
        document=ChunkArtifactDocument(
            document_id=_DOCUMENT_ID,
            filename="test.pdf",
            parser="docling",
        ),
        strategy=ChunkArtifactStrategy(
            strategy=ChunkingStrategy.FIXED,
            strategy_version="1.0",
            configuration_fingerprint="fingerprint",
        ),
        statistics=ChunkArtifactStatistics(),
        chunks=chunks,
    )


def _make_model(*, dimensions: int = 3) -> MagicMock:
    model = MagicMock()
    model.encode.side_effect = lambda texts, **_: np.array(
        [[float(i)] * dimensions for i in range(len(texts))]
    )
    return model


def test_provider_identifiers_reflect_configuration() -> None:
    config = SentenceTransformerEmbeddingConfig(model_name="all-MiniLM-L6-v2")
    provider = SentenceTransformerEmbeddingProvider(config)

    assert provider.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS
    assert provider.model == "all-MiniLM-L6-v2"


async def test_embed_converts_encoded_vectors_into_canonical_embeddings() -> None:
    with patch(
        "app.ai.knowledge.embeddings.providers.sentence_transformers.SentenceTransformer",
        return_value=_make_model(dimensions=4),
    ):
        provider = SentenceTransformerEmbeddingProvider(
            SentenceTransformerEmbeddingConfig(batch_size=10),
        )

        chunk = _make_chunk("hello world")
        artifact = _make_chunk_artifact([chunk])

        embeddings = await provider.embed(artifact)

    assert len(embeddings) == 1
    embedding = embeddings[0]

    assert embedding.provenance.document_id == chunk.provenance.document_id
    assert embedding.provenance.chunk_id == chunk.id
    assert embedding.provider.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS
    assert embedding.provider.model == provider.model
    assert embedding.vector.values == [0.0, 0.0, 0.0, 0.0]
    assert embedding.vector.dimensions == 4
    assert embedding.experiment.configuration_fingerprint == provider.configuration_fingerprint


async def test_embed_constructs_model_lazily_and_only_once() -> None:
    with patch(
        "app.ai.knowledge.embeddings.providers.sentence_transformers.SentenceTransformer",
        return_value=_make_model(),
    ) as sentence_transformer_cls:
        provider = SentenceTransformerEmbeddingProvider(
            SentenceTransformerEmbeddingConfig(batch_size=10),
        )

        sentence_transformer_cls.assert_not_called()

        artifact = _make_chunk_artifact([_make_chunk("hello world")])

        await provider.embed(artifact)
        await provider.embed(artifact)

        sentence_transformer_cls.assert_called_once_with(
            model_name_or_path=provider.config.model_name,
            device=provider.config.device,
            trust_remote_code=provider.config.trust_remote_code,
        )
