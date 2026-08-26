from __future__ import annotations

import pytest
from app.ai.runtime.voice.create import create_voice_stt_provider, create_voice_tts_provider
from app.core.settings import settings


def _clear_caches() -> None:
    create_voice_stt_provider.cache_clear()
    create_voice_tts_provider.cache_clear()


@pytest.fixture(autouse=True)
def _isolated_lru_cache():
    """Both factories are `@lru_cache`d singletons -- clear before and
    after every test so a provider built under one test's monkeypatched
    settings can't leak into the next test (or into a different test
    file) via the cache."""

    _clear_caches()
    yield
    _clear_caches()


def test_stt_provider_is_none_when_api_key_unset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "deepgram_api_key", None)

    assert create_voice_stt_provider() is None


def test_stt_provider_is_built_when_api_key_set(monkeypatch) -> None:
    monkeypatch.setattr(settings, "deepgram_api_key", "dg-secret")

    provider = create_voice_stt_provider()

    assert provider is not None


def test_tts_provider_is_none_when_api_key_unset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "elevenlabs_api_key", None)
    monkeypatch.setattr(settings, "elevenlabs_voice_id", "voice-123")

    assert create_voice_tts_provider() is None


def test_tts_provider_is_none_when_voice_id_unset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "elevenlabs_api_key", "el-secret")
    monkeypatch.setattr(settings, "elevenlabs_voice_id", None)

    assert create_voice_tts_provider() is None


def test_tts_provider_is_built_when_both_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "elevenlabs_api_key", "el-secret")
    monkeypatch.setattr(settings, "elevenlabs_voice_id", "voice-123")

    provider = create_voice_tts_provider()

    assert provider is not None
