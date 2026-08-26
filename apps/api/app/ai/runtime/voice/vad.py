"""Minimal energy-based voice-activity detection for barge-in
(docs/todo/voice-chat-poc-implementation-plan.md T10): detects the user
starting to speak again while a response is still playing, without
opening a second live Deepgram connection during playback -- cheaper, and
avoids running two concurrent STT sessions per turn. This is deliberately
simple (RMS amplitude over a threshold, for a run of consecutive chunks)
rather than a trained VAD model; good enough to demonstrate the mechanism,
not tuned against real audio yet -- see the plan doc's T10/T11 notes.
"""

from __future__ import annotations

import array
import math


def pcm16_rms(chunk: bytes) -> float:
    """Root-mean-square amplitude of a 16-bit little-endian PCM chunk.
    Empty or odd-length (partial-sample) input is treated as silence
    rather than raising -- a truncated frame is not a real error here.

    Deliberately plain Python (`array`), not the stdlib `audioop` module:
    `audioop` was deprecated in 3.11 and removed outright in 3.13 (PEP
    594) -- this repo pins `<3.13` today, but writing new code against a
    module already scheduled for removal is worth avoiding, not worth the
    (tiny) performance difference for one RMS calculation per chunk."""

    usable_length = len(chunk) - (len(chunk) % 2)
    if usable_length < 2:
        return 0.0

    samples = array.array("h")  # signed 16-bit
    samples.frombytes(chunk[:usable_length])
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    return math.sqrt(mean_square)


class BargeInDetector:
    """Tracks consecutive above-threshold chunks; `push()` returns `True`
    the moment the run reaches `consecutive_chunks_required`, and stays
    `True`-only-once (a detector instance is meant to be used for exactly
    one turn's response playback, then discarded)."""

    def __init__(self, *, rms_threshold: float, consecutive_chunks_required: int) -> None:
        self._rms_threshold = rms_threshold
        self._consecutive_chunks_required = max(1, consecutive_chunks_required)
        self._consecutive_count = 0

    def push(self, chunk: bytes) -> bool:
        if pcm16_rms(chunk) >= self._rms_threshold:
            self._consecutive_count += 1
        else:
            self._consecutive_count = 0

        return self._consecutive_count >= self._consecutive_chunks_required
