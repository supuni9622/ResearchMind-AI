"""Buffers streamed generation-token deltas into sentence-sized chunks for
TTS, so audio synthesis starts on the first complete sentence rather than
waiting for the whole response (docs/todo/voice-chat-poc-implementation-plan.md
T8)."""

from __future__ import annotations

_SENTENCE_END_CHARS = (".", "!", "?", "\n")


class SentenceBuffer:
    def __init__(self, max_chars: int = 200) -> None:
        self._buffer = ""
        self._max_chars = max_chars

    def push(self, delta: str) -> list[str]:
        """Feeds one token delta in; returns zero or more complete
        sentences now ready to synthesize."""

        self._buffer += delta
        ready: list[str] = []

        while True:
            split_at = self._find_split_point()
            if split_at is None:
                break
            chunk = self._buffer[:split_at].strip()
            self._buffer = self._buffer[split_at:]
            if chunk:
                ready.append(chunk)

        return ready

    def _find_split_point(self) -> int | None:
        for index, char in enumerate(self._buffer):
            if char in _SENTENCE_END_CHARS:
                return index + 1

        if len(self._buffer) >= self._max_chars:
            # No sentence boundary yet but the buffer is getting long
            # enough to hurt time-to-first-audio -- force a split at the
            # nearest word boundary instead of waiting indefinitely for
            # punctuation.
            space_index = self._buffer.rfind(" ", 0, self._max_chars)
            return space_index + 1 if space_index > 0 else self._max_chars

        return None

    def flush(self) -> str | None:
        """Call once the response is complete -- returns any trailing
        partial sentence still sitting in the buffer, or `None`."""

        remaining = self._buffer.strip()
        self._buffer = ""
        return remaining or None
