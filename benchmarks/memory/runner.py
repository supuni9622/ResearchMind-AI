"""CLI for scoring captured M6 memory retrieval results."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from benchmarks.common.report_generator import BenchmarkReportGenerator
from benchmarks.memory.benchmark import score_memory_candidate
from benchmarks.memory.dataset import load_memory_evaluation_dataset
from benchmarks.memory.results import load_memory_candidate_results

MIN_RECALL_AT_5 = 0.8
MAX_AVG_LATENCY_MS = 500.0
MAX_AVG_SELECTED_TOKENS = 1200.0


def release_gate_failures(metrics: Mapping[str, Any]) -> list[str]:
    """Return the metric names that violate the provisional M6 gate."""
    failed: list[str] = []
    for name in (
        "scope_leak_rate",
        "unsafe_memory_injection_rate",
        "stale_injection_rate",
        "contradictory_injection_rate",
    ):
        if float(metrics[name]) > 0:
            failed.append(name)
    if float(metrics["recall_at_5"]) < MIN_RECALL_AT_5:
        failed.append("recall_at_5")
    if float(metrics["avg_latency_ms"]) > MAX_AVG_LATENCY_MS:
        failed.append("avg_latency_ms")
    if float(metrics["avg_selected_tokens"]) > MAX_AVG_SELECTED_TOKENS:
        failed.append("avg_selected_tokens")
    return failed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/reports/memory"))
    args = parser.parse_args()

    report = score_memory_candidate(
        dataset=load_memory_evaluation_dataset(args.dataset),
        captured=load_memory_candidate_results(args.results),
    )
    generator = BenchmarkReportGenerator()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(generator.generate_json(report), encoding="utf-8")
    (args.output / "report.md").write_text(generator.generate_markdown(report), encoding="utf-8")

    metrics = report.candidates[0].metrics
    failed = release_gate_failures(metrics)
    if failed:
        print(f"Memory release gate FAILED: {', '.join(failed)}")
        sys.exit(1)
    print(f"Memory benchmark passed; reports written to {args.output}")


if __name__ == "__main__":
    main()
