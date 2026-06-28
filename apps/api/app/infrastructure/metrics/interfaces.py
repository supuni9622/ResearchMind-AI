from abc import ABC, abstractmethod


class MetricsRecorder(ABC):
    """Abstract metrics recorder."""

    @abstractmethod
    def record_duration(
        self,
        *,
        operation: str,
        duration_ms: float,
    ) -> None: ...

    @abstractmethod
    def increment(
        self,
        *,
        metric: str,
    ) -> None: ...
