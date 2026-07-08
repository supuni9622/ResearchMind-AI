"""
Unit tests for FastEmbedSparseEmbeddingProvider.

Covers:
- Empty input short-circuits without calling the model
- The underlying model is invoked with the configured batch size, and
  output order/values are preserved when converted into SparseVector
- Model failures are wrapped in SparseEmbeddingError
- Provider identifiers reflect the configured model

A fake model is always injected via the `model` constructor argument so
these tests never trigger a real SPLADE model load/download.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.ai.knowledge.indexing.exceptions import SparseEmbeddingError
from app.ai.knowledge.indexing.providers.fastembed import (
    FastEmbedSparseEmbeddingConfig,
    FastEmbedSparseEmbeddingProvider,
)


def _fake_sparse_embedding(indices: list[int], values: list[float]) -> SimpleNamespace:
    """Stand-in for fastembed's SparseEmbedding (has .indices / .values)."""

    return SimpleNamespace(indices=indices, values=values)


def _make_model(return_value: list[SimpleNamespace]) -> MagicMock:
    model = MagicMock()
    model.embed.return_value = return_value
    return model


def test_provider_identifiers_reflect_configuration() -> None:
    config = FastEmbedSparseEmbeddingConfig(model_name="custom/splade-model")
    provider = FastEmbedSparseEmbeddingProvider(config=config, model=_make_model([]))

    assert provider.model == "custom/splade-model"
    assert provider.version == "1.0"
    assert provider.config is config


async def test_embed_returns_empty_list_without_calling_model() -> None:
    model = _make_model([])
    provider = FastEmbedSparseEmbeddingProvider(
        config=FastEmbedSparseEmbeddingConfig(),
        model=model,
    )

    result = await provider.embed([])

    assert result == []
    model.embed.assert_not_called()


async def test_embed_calls_model_with_configured_batch_size() -> None:
    model = _make_model([_fake_sparse_embedding([1], [0.5]), _fake_sparse_embedding([2], [0.6])])
    config = FastEmbedSparseEmbeddingConfig(batch_size=8)
    provider = FastEmbedSparseEmbeddingProvider(config=config, model=model)

    await provider.embed(["alpha", "beta"])

    model.embed.assert_called_once_with(["alpha", "beta"], batch_size=8)


async def test_embed_converts_output_into_ordered_sparse_vectors() -> None:
    model = _make_model(
        [
            _fake_sparse_embedding([3, 7], [0.1, 0.2]),
            _fake_sparse_embedding([9], [0.9]),
        ]
    )
    provider = FastEmbedSparseEmbeddingProvider(
        config=FastEmbedSparseEmbeddingConfig(),
        model=model,
    )

    result = await provider.embed(["first text", "second text"])

    assert len(result) == 2
    assert result[0].indices == [3, 7]
    assert result[0].values == [0.1, 0.2]
    assert result[1].indices == [9]
    assert result[1].values == [0.9]
    assert all(isinstance(value, float) for value in result[0].values)
    assert all(isinstance(index, int) for index in result[0].indices)


async def test_embed_wraps_model_failures_in_sparse_embedding_error() -> None:
    model = MagicMock()
    model.embed.side_effect = RuntimeError("onnx runtime blew up")
    provider = FastEmbedSparseEmbeddingProvider(
        config=FastEmbedSparseEmbeddingConfig(),
        model=model,
    )

    with pytest.raises(SparseEmbeddingError):
        await provider.embed(["text"])
