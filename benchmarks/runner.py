"""
Benchmark runner.

Executes engineering benchmarks and generates benchmark reports.

The runner is intentionally benchmark-agnostic. Individual benchmark
implementations are registered with the BenchmarkRegistry.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from benchmarks.common.report_generator import BenchmarkReportGenerator
from benchmarks.factory import create_benchmark_registry


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

    args = parser.parse_args()

    registry = create_benchmark_registry()

    benchmark = registry.get(args.benchmark)

    report = await benchmark.run(
        args.dataset,
    )

    generator = BenchmarkReportGenerator()

    output_directory = args.output / args.benchmark.lower()
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

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


if __name__ == "__main__":
    asyncio.run(main())
