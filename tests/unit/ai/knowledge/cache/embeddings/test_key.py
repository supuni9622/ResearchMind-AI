"""
Unit tests for build_embedding_cache_key.

Covers:
- Identical inputs produce identical keys
- Provider, model, configuration fingerprint, and text are all part of
  the key, so changing any one of them changes the key
"""

from __future__ import annotations

from app.ai.knowledge.cache.embeddings.key import build_embedding_cache_key
from app.ai.knowledge.embeddings.enums import EmbeddingProvider


def _key(**overrides: object) -> str:
    defaults: dict[str, object] = {
        "provider": EmbeddingProvider.SENTENCE_TRANSFORMERS,
        "model": "all-MiniLM-L6-v2",
        "configuration_fingerprint": "fingerprint",
        "text": "hello world",
    }
    defaults.update(overrides)
    return build_embedding_cache_key(**defaults)  # type: ignore[arg-type]


def test_identical_inputs_produce_identical_keys() -> None:
    assert _key() == _key()


def test_different_provider_changes_the_key() -> None:
    assert _key(provider=EmbeddingProvider.VOYAGE_AI) != _key()


def test_different_model_changes_the_key() -> None:
    assert _key(model="a-different-model") != _key()


def test_different_configuration_fingerprint_changes_the_key() -> None:
    assert _key(configuration_fingerprint="different-fingerprint") != _key()


def test_different_text_changes_the_key() -> None:
    assert _key(text="a different chunk") != _key()


def test_key_is_namespaced_by_provider() -> None:
    key = _key()

    assert key.startswith(f"embedding-cache:{EmbeddingProvider.SENTENCE_TRANSFORMERS.value}:")
