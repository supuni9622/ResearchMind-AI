"""
Unit tests for GenerationRegistry.

Covers:
- Providers passed to __init__ are resolvable via get()
- get() raises GenerationProviderNotFoundError for an unregistered provider
- has() reflects registration state
- providers property lists the registered provider keys
- An empty registry has no providers
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.exceptions import GenerationProviderNotFoundError
from app.ai.runtime.generation.interfaces import (
    GenerationProviderInterface,
)
from app.ai.runtime.generation.registry import GenerationRegistry


def _make_provider(provider: GenerationProvider) -> MagicMock:
    fake = MagicMock(spec=GenerationProviderInterface)
    fake.provider = provider
    return fake


def test_get_returns_the_registered_provider() -> None:
    provider = _make_provider(GenerationProvider.GROQ)
    registry = GenerationRegistry(providers=[provider])

    assert registry.get(GenerationProvider.GROQ) is provider


def test_get_raises_not_found_error_for_unregistered_provider() -> None:
    registry = GenerationRegistry(providers=[])

    with pytest.raises(GenerationProviderNotFoundError, match="groq"):
        registry.get(GenerationProvider.GROQ)


def test_has_returns_true_for_registered_provider() -> None:
    registry = GenerationRegistry(providers=[_make_provider(GenerationProvider.OPENAI)])

    assert registry.has(GenerationProvider.OPENAI) is True


def test_has_returns_false_for_unregistered_provider() -> None:
    registry = GenerationRegistry(providers=[])

    assert registry.has(GenerationProvider.OPENAI) is False


def test_providers_property_lists_registered_provider_keys() -> None:
    registry = GenerationRegistry(
        providers=[
            _make_provider(GenerationProvider.GROQ),
            _make_provider(GenerationProvider.CLAUDE),
        ]
    )

    assert set(registry.providers) == {
        GenerationProvider.GROQ,
        GenerationProvider.CLAUDE,
    }


def test_empty_registry_has_no_providers() -> None:
    registry = GenerationRegistry(providers=[])

    assert registry.providers == []
    assert registry.has(GenerationProvider.GEMINI) is False


def test_registering_the_same_provider_key_twice_keeps_the_last_one() -> None:
    first = _make_provider(GenerationProvider.OLLAMA)
    second = _make_provider(GenerationProvider.OLLAMA)

    registry = GenerationRegistry(providers=[first, second])

    assert registry.get(GenerationProvider.OLLAMA) is second
    assert registry.providers == [GenerationProvider.OLLAMA]
