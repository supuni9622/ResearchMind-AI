from abc import ABC, abstractmethod


class MetricsRecorder(ABC):
    """Abstract metrics recorder.

    `labels` is optional and additive (Prometheus Grafana Observability
    PRD §13/§15) -- existing call sites that only pass `operation`/
    `metric` keep working unchanged against any implementation.
    Implementations must treat an unrecognized metric name or an
    unrecognized label key as a no-op, never as an error.
    """

    @abstractmethod
    def record_duration(
        self,
        *,
        operation: str,
        duration_ms: float,
        labels: dict[str, str] | None = None,
    ) -> None: ...

    @abstractmethod
    def increment(
        self,
        *,
        metric: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None: ...

    @abstractmethod
    def set_gauge(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None: ...

    @abstractmethod
    def observe(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Records a raw value (not a duration) into a histogram -- e.g. a
        result count or evidence count. `record_duration` remains the
        entry point for latency histograms."""
        ...
