"""
Integration tests for WS /api/v1/chat/voice -- the fail-closed paths only
(docs/todo/voice-chat-poc-implementation-plan.md).

Covers the two checks that run before any auth/DB/vendor work starts, so
they need no database session and no Deepgram/ElevenLabs/ChatService
fakes:
- `settings.voice_enabled = False` closes immediately.
- `voice_enabled = True` but no Deepgram API key configured closes
  immediately (mirrors the rest of this app's "unconfigured deployment
  never crashes" convention).

A full mocked turn (auth + Deepgram + ChatService + ElevenLabs all faked)
is a known gap, not attempted here -- `WS /chat/ws` itself has no
integration test either (this repo has none for any WebSocket route yet),
so this file's scope is deliberately the same "fails closed" shape as
what's already proven safe elsewhere, not a claim of full coverage.
"""

from __future__ import annotations

import pytest
from app.ai.runtime.voice.create import create_voice_stt_provider, create_voice_tts_provider
from app.core.settings import settings
from app.main import app
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture(autouse=True)
def _isolated_voice_provider_cache():
    create_voice_stt_provider.cache_clear()
    create_voice_tts_provider.cache_clear()
    yield
    create_voice_stt_provider.cache_clear()
    create_voice_tts_provider.cache_clear()


def test_voice_websocket_closes_when_voice_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voice_enabled", False)

    client = TestClient(app)
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect("/api/v1/chat/voice?token=irrelevant") as ws,
    ):
        ws.receive_text()

    assert exc_info.value.code == 1008
    assert exc_info.value.reason == "Voice is not enabled."


def test_voice_websocket_closes_when_stt_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voice_enabled", True)
    monkeypatch.setattr(settings, "deepgram_api_key", None)

    client = TestClient(app)
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect("/api/v1/chat/voice?token=irrelevant") as ws,
    ):
        ws.receive_text()

    assert exc_info.value.code == 1008
    assert exc_info.value.reason == "Voice speech-to-text is not configured."
