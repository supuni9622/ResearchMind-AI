"""
Benchmark registry.

The BenchmarkRegistry provides a central lookup mechanism for
engineering benchmarks.

Benchmarks register themselves using a unique name and can later be
resolved by the benchmark runner.

The registry is intentionally lightweight and contains no construction
logic. Dependency injection remains the responsibility of the benchmark
runner (or a future benchmark factory).
"""

from __future__ import annotations

from benchmarks.interfaces.benchmark import Benchmark


class BenchmarkRegistry:
    """
    Registry of engineering benchmarks.
    """

    def __init__(self) -> None:
        self._benchmarks: dict[str, Benchmark] = {}

    def register(
        self,
        benchmark: Benchmark,
    ) -> None:
        """
        Register a benchmark.

        Raises:
            ValueError:
                If a benchmark with the same name has already been
                registered.
        """

        name = benchmark.name.lower()

        if name in self._benchmarks:
            raise ValueError(f"Benchmark '{name}' is already registered.")

        self._benchmarks[name] = benchmark

    def get(
        self,
        name: str,
    ) -> Benchmark:
        """
        Resolve a registered benchmark.

        Raises:
            KeyError:
                If the benchmark is not registered.
        """

        try:
            return self._benchmarks[name.lower()]
        except KeyError:
            raise KeyError(f"Benchmark '{name}' is not registered.") from None

    @property
    def benchmarks(
        self,
    ) -> dict[str, Benchmark]:
        """
        Registered benchmarks.
        """

        return self._benchmarks.copy()
