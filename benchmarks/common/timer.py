"""
Benchmark timing utility.

Provides a small, dependency-free timer for measuring the latency and
throughput of benchmark candidates.
"""

from __future__ import annotations

import time
from types import TracebackType


class Timer:
    """
    High-resolution execution timer.

    Can be used explicitly via start()/stop() or as a context manager.
    """

    def __init__(self) -> None:
        self._start_time: float | None = None
        self._end_time: float | None = None

    def start(self) -> None:
        """
        Start the timer.
        """

        self._start_time = time.perf_counter()
        self._end_time = None

    def stop(self) -> None:
        """
        Stop the timer.
        """

        if self._start_time is None:
            raise RuntimeError("Timer has not been started.")

        self._end_time = time.perf_counter()

    @property
    def elapsed_seconds(self) -> float:
        """
        Elapsed time in seconds.

        If the timer has not been stopped yet, returns the time elapsed
        so far.
        """

        if self._start_time is None:
            raise RuntimeError("Timer has not been started.")

        end_time = self._end_time or time.perf_counter()
        return end_time - self._start_time

    @property
    def elapsed_milliseconds(self) -> float:
        """
        Elapsed time in milliseconds.
        """

        return self.elapsed_seconds * 1000

    def __enter__(self) -> Timer:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()
