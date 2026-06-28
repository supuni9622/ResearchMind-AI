from app.infrastructure.metrics.interfaces import MetricsRecorder


class NoOpMetricsRecorder(MetricsRecorder):
    """Placeholder metrics implementation."""

    def record_duration(
        self,
        *,
        operation: str,
        duration_ms: float,
    ) -> None:
        return

    def increment(
        self,
        *,
        metric: str,
    ) -> None:
        return


# Until Prometheus is added, use a no-op implementation.
# This lets us instrument the code now without introducing Prometheus dependencies.
