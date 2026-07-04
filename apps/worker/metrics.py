"""
Worker runtime metrics.

These metrics provide lightweight observability for the processing
worker during development and production. They are maintained
in-memory and reset whenever the worker restarts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WorkerMetrics:
    """
    In-memory processing worker metrics.
    """

    processed_jobs: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    retried_jobs: int = 0
    dead_letter_jobs: int = 0

    total_processing_time_ms: float = 0.0

    @property
    def average_processing_time_ms(
        self,
    ) -> float:
        """
        Average processing duration.
        """

        if self.processed_jobs == 0:
            return 0.0

        return round(
            self.total_processing_time_ms / self.processed_jobs,
            2,
        )
