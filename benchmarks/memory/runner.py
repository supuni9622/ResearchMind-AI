"""CLI for scoring captured M6 memory retrieval results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from benchmarks.common.report_generator import BenchmarkReportGenerator
from benchmarks.memory.benchmark import score_memory_candidate
from benchmarks.memory.dataset import load_memory_evaluation_dataset
from benchmarks.memory.results import load_memory_candidate_results


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
    failed = [
        name
        for name in ("scope_leak_rate", "unsafe_memory_injection_rate")
        if float(metrics[name]) > 0
    ]
    if failed:
        print(f"Memory release gate FAILED: {', '.join(failed)}")
        sys.exit(1)
    print(f"Memory benchmark passed; reports written to {args.output}")


if __name__ == "__main__":
    main()
