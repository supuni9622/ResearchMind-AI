from __future__ import annotations

import array
import math

from app.ai.runtime.voice.vad import BargeInDetector, pcm16_rms


def _pcm16(amplitude: int, sample_count: int = 160) -> bytes:
    samples = array.array("h", [amplitude] * sample_count)
    return samples.tobytes()


def test_pcm16_rms_of_silence_is_zero() -> None:
    assert pcm16_rms(_pcm16(0)) == 0.0


def test_pcm16_rms_of_constant_amplitude_equals_that_amplitude() -> None:
    # RMS of a constant-value signal is just that value's magnitude.
    assert math.isclose(pcm16_rms(_pcm16(1000)), 1000.0)


def test_pcm16_rms_handles_empty_and_odd_length_input_as_silence() -> None:
    assert pcm16_rms(b"") == 0.0
    assert pcm16_rms(b"\x01") == 0.0


def test_barge_in_detector_requires_consecutive_loud_chunks() -> None:
    detector = BargeInDetector(rms_threshold=500.0, consecutive_chunks_required=3)

    assert detector.push(_pcm16(1000)) is False
    assert detector.push(_pcm16(1000)) is False
    assert detector.push(_pcm16(1000)) is True


def test_barge_in_detector_resets_the_run_on_a_quiet_chunk() -> None:
    detector = BargeInDetector(rms_threshold=500.0, consecutive_chunks_required=3)

    assert detector.push(_pcm16(1000)) is False
    assert detector.push(_pcm16(1000)) is False
    assert detector.push(_pcm16(0)) is False  # quiet chunk resets the run
    assert detector.push(_pcm16(1000)) is False
    assert detector.push(_pcm16(1000)) is False
    assert detector.push(_pcm16(1000)) is True


def test_barge_in_detector_ignores_chunks_below_threshold() -> None:
    detector = BargeInDetector(rms_threshold=500.0, consecutive_chunks_required=2)

    for _ in range(10):
        assert detector.push(_pcm16(100)) is False
