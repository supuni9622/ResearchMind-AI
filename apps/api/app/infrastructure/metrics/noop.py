from app.infrastructure.metrics.interfaces import MetricsRecorder


class NoOpMetricsRecorder(MetricsRecorder):
    """Placeholder metrics implementation."""

    def record_duration(
        self,
        *,
        operation: str,
        duration_ms: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        return

    def increment(
        self,
        *,
        metric: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        return

    def set_gauge(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        return

    def observe(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        return


# Used whenever Prometheus is disabled (PROMETHEUS_ENABLED=false) or a
# platform hasn't been wired to a recorder yet.
