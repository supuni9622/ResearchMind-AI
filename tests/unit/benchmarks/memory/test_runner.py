from benchmarks.memory.runner import release_gate_failures


def _passing_metrics() -> dict[str, float]:
    return {
        "scope_leak_rate": 0.0,
        "unsafe_memory_injection_rate": 0.0,
        "stale_injection_rate": 0.0,
        "contradictory_injection_rate": 0.0,
        "recall_at_5": 0.9,
        "avg_latency_ms": 100.0,
        "avg_selected_tokens": 500.0,
    }


def test_release_gate_accepts_metrics_within_budget() -> None:
    assert release_gate_failures(_passing_metrics()) == []


def test_release_gate_reports_every_violated_metric() -> None:
    metrics = _passing_metrics()
    metrics.update(
        {
            "scope_leak_rate": 0.1,
            "unsafe_memory_injection_rate": 0.1,
            "stale_injection_rate": 0.1,
            "contradictory_injection_rate": 0.1,
            "recall_at_5": 0.7,
            "avg_latency_ms": 501.0,
            "avg_selected_tokens": 1201.0,
        }
    )

    assert release_gate_failures(metrics) == [
        "scope_leak_rate",
        "unsafe_memory_injection_rate",
        "stale_injection_rate",
        "contradictory_injection_rate",
        "recall_at_5",
        "avg_latency_ms",
        "avg_selected_tokens",
    ]
