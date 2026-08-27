"""Voice-on-Chat POC composition root (docs/todo/voice-chat-poc-implementation-plan.md).

Mirrors `app.ai.tools.web_search.create.create_web_search_service`'s
"register only if configured" pattern: an absent API key (or, for
ElevenLabs, an absent voice ID) degrades the corresponding factory to
`None` rather than raising, so an unconfigured deployment never crashes --
`WS /chat/voice` itself closes the connection with a clear reason when its
required provider is unavailable, same shape as every other optional
integration in this app.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.runtime.voice.stt.deepgram import DeepgramSTTProvider
from app.ai.runtime.voice.tts.elevenlabs import ElevenLabsTTSProvider
from app.core.settings import settings


@lru_cache
def create_voice_stt_provider() -> DeepgramSTTProvider | None:
    if not settings.deepgram_api_key:
        return None

    return DeepgramSTTProvider(
        api_key=settings.deepgram_api_key,
        model=settings.deepgram_model,
        sample_rate=settings.deepgram_sample_rate,
        endpointing_ms=settings.deepgram_endpointing_ms,
        connect_timeout_seconds=settings.voice_stt_connect_timeout_seconds,
    )


@lru_cache
def create_voice_tts_provider() -> ElevenLabsTTSProvider | None:
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        return None

    return ElevenLabsTTSProvider(
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id,
        model_id=settings.elevenlabs_model_id,
        output_format=settings.elevenlabs_output_format,
        connect_timeout_seconds=settings.voice_tts_connect_timeout_seconds,
    )
