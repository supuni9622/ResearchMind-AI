"""
Ingestion fidelity benchmark.

Checks parse fidelity -- did Docling preserve a document's actual
heading/table structure -- against a handful of hand-verified fixture
documents (EVALUATION_PLAN.md §4's MVP slice: parse success rate +
heading/table preservation). Run this when changing Docling
configuration, chunking strategy, or the canonical document schema --
the same trigger already used for `benchmarks/chunking/`, extended here
to fidelity rather than only strategy comparison.
"""

from __future__ import annotations

from pathlib import Path

from benchmarks.ingestion.fixtures import (
    load_fixture_document,
    load_fixture_manifest,
)
from benchmarks.ingestion.metrics import (
    extract_markdown_structure,
    parse_success_rate,
    preservation_score,
)
from benchmarks.interfaces.benchmark import Benchmark
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkReport,
)


class IngestionFidelityBenchmark(Benchmark):
    """
    Engineering benchmark for ingestion parse fidelity.
    """

    @property
    def name(self) -> str:
        return "IngestionFidelity"

    async def run(
        self,
        dataset_path: Path,
    ) -> BenchmarkReport:
        """
        Execute the ingestion fidelity benchmark.

        Args:
            dataset_path:
                Root benchmark dataset directory (containing
                `ingestion_fidelity_fixtures.json` and each fixture's
                `paper-NNN/processed_document.json`).

        Returns:
            Canonical benchmark report with one candidate ("Docling").
        """

        manifest = load_fixture_manifest(dataset_path)

        parse_outcomes: list[bool] = []
        heading_scores: list[float] = []
        table_scores: list[float] = []
        per_fixture_notes: dict[str, object] = {}

        for fixture in manifest.fixtures:
            document = load_fixture_document(dataset_path, fixture)

            parse_outcomes.append(document is not None)

            if document is None:
                heading_scores.append(0.0)
                table_scores.append(0.0)
                per_fixture_notes[fixture.document_dir] = {"parsed": False}
                continue

            structure = extract_markdown_structure(document.markdown)

            heading_score = preservation_score(
                actual_count=structure.heading_count,
                expected_min_count=fixture.expected_min_headings,
            )
            table_score = preservation_score(
                actual_count=structure.table_count,
                expected_min_count=fixture.expected_min_tables,
            )

            heading_scores.append(heading_score)
            table_scores.append(table_score)

            per_fixture_notes[fixture.document_dir] = {
                "parsed": True,
                "heading_count": structure.heading_count,
                "expected_min_headings": fixture.expected_min_headings,
                "table_count": structure.table_count,
                "expected_min_tables": fixture.expected_min_tables,
            }

        candidate = BenchmarkCandidate(
            name="Docling",
            metrics={
                "parse_success_rate": round(parse_success_rate(parse_outcomes), 4),
                "heading_preservation_score": (
                    round(sum(heading_scores) / len(heading_scores), 4) if heading_scores else 0.0
                ),
                "table_preservation_score": (
                    round(sum(table_scores) / len(table_scores), 4) if table_scores else 0.0
                ),
                "fixtures_evaluated": len(manifest.fixtures),
            },
            notes={"per_fixture": per_fixture_notes},
        )

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name="research-papers/ingestion-fidelity",
                document_count=len(manifest.fixtures),
            ),
            candidates=[candidate],
        )
