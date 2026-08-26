from __future__ import annotations

from app.ai.runtime.voice.sentence_buffer import SentenceBuffer


def test_push_returns_nothing_until_a_sentence_boundary_arrives() -> None:
    buffer = SentenceBuffer()

    assert buffer.push("The quick") == []
    assert buffer.push(" brown fox") == []
    assert buffer.push(" jumps.") == ["The quick brown fox jumps."]


def test_push_can_yield_multiple_sentences_from_one_delta() -> None:
    buffer = SentenceBuffer()

    assert buffer.push("First one. Second one!") == ["First one.", "Second one!"]


def test_push_force_splits_a_long_run_with_no_punctuation() -> None:
    buffer = SentenceBuffer(max_chars=20)

    ready = buffer.push("this sentence never ends and keeps going and going")

    assert ready
    assert all(len(chunk) <= 20 for chunk in ready)
    # Nothing was silently dropped -- flushing what's left plus the
    # already-yielded chunks reconstructs (modulo whitespace) the input.
    remaining = buffer.flush() or ""
    assert "".join(ready).replace(" ", "") + remaining.replace(" ", "") == (
        "this sentence never ends and keeps going and going".replace(" ", "")
    )


def test_flush_returns_trailing_partial_sentence() -> None:
    buffer = SentenceBuffer()
    buffer.push("No terminal punctuation yet")

    assert buffer.flush() == "No terminal punctuation yet"
    # Flushing again after empty is None, not an empty string.
    assert buffer.flush() is None


def test_flush_returns_none_when_buffer_is_empty() -> None:
    buffer = SentenceBuffer()

    assert buffer.flush() is None
