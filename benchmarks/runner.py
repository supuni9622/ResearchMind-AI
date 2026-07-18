"""
Benchmark runner.

Executes engineering benchmarks and generates benchmark reports.

The runner is intentionally benchmark-agnostic. Individual benchmark
implementations are registered with the BenchmarkRegistry.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from benchmarks.common.report_generator import BenchmarkReportGenerator
from benchmarks.factory import create_benchmark_registry
from benchmarks.models.report import BenchmarkReport
from benchmarks.regression.detector import RegressionDetector
from benchmarks.regression.report_generator import RegressionReportGenerator


async def main() -> None:
    """
    Benchmark runner entry point.
    """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "benchmark",
        help="Benchmark name (e.g. chunking)",
    )

    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Benchmark dataset directory.",
    )

    parser.add_argument(
        "--output",
        default=Path("benchmarks/reports"),
        type=Path,
        help="Output directory.",
    )

    parser.add_argument(
        "--check-regression",
        action="store_true",
        help=(
            "Compare this run against the previously stored report.json in the "
            "output directory and exit non-zero if any metric regressed beyond "
            "its threshold (see benchmarks/regression/thresholds.py)."
        ),
    )

    args = parser.parse_args()

    registry = create_benchmark_registry()

    benchmark = registry.get(args.benchmark)

    output_directory = args.output / args.benchmark.lower()
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    previous_report: BenchmarkReport | None = None
    previous_report_path = output_directory / "report.json"

    if args.check_regression and previous_report_path.exists():
        previous_report = BenchmarkReport.model_validate_json(
            previous_report_path.read_text(encoding="utf-8"),
        )

    report = await benchmark.run(
        args.dataset,
    )

    generator = BenchmarkReportGenerator()

    markdown_report = generator.generate_markdown(
        report,
    )

    json_report = generator.generate_json(
        report,
    )

    (output_directory / "report.md").write_text(
        markdown_report,
        encoding="utf-8",
    )

    (output_directory / "report.json").write_text(
        json_report,
        encoding="utf-8",
    )

    print(f"Benchmark completed: {benchmark.name}")
    print(f"Reports written to: {output_directory}")

    if not args.check_regression:
        return

    if previous_report is None:
        print("No previous report.json found — nothing to compare against yet.")
        return

    regression_result = RegressionDetector().compare(
        previous=previous_report,
        current=report,
    )

    regression_generator = RegressionReportGenerator()

    (output_directory / "regression.json").write_text(
        regression_generator.generate_json(regression_result),
        encoding="utf-8",
    )

    (output_directory / "regression_report.md").write_text(
        regression_generator.generate_markdown(regression_result),
        encoding="utf-8",
    )

    if not regression_result.passed:
        print(f"Regression check FAILED ({len(regression_result.regressions)} issue(s)):")

        for issue in regression_result.regressions:
            print(f"  - {issue.candidate} / {issue.message}")

        sys.exit(1)

    print("Regression check passed.")


if __name__ == "__main__":
    asyncio.run(main())
