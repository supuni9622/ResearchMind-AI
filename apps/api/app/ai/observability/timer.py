from __future__ import annotations

import time


class Timer:
    """High-resolution execution timer."""

    def __init__(self) -> None:
        self._start_time: float | None = None
        self._end_time: float | None = None

    def start(self) -> None:
        """Start the timer."""
        self._start_time = time.perf_counter()
        self._end_time = None

    def stop(self) -> None:
        """Stop the timer."""
        if self._start_time is None:
            raise RuntimeError("Timer has not been started.")

        self._end_time = time.perf_counter()

    @property
    def elapsed_seconds(self) -> float:
        """Return the elapsed time in seconds."""
        if self._start_time is None:
            raise RuntimeError("Timer has not been started.")

        end_time = self._end_time or time.perf_counter()
        return end_time - self._start_time

    @property
    def elapsed_milliseconds(self) -> float:
        """Return the elapsed time in milliseconds."""
        return self.elapsed_seconds * 1000
