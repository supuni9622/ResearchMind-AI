# Evaluation Pipeline

**Status:** Implemented as an offline engineering-benchmark pipeline (`benchmarks/`). Not the same thing as a RAG-quality/golden-QA evaluation pipeline — see `docs/evaluation/strategy.md` for what's still missing on that front.

---

## What this pipeline actually is

Runs the **real, unmocked production pipeline** (Chunking → Embedding → Indexing) against a benchmark dataset, measures it, and can gate on regression. Upload and PDF-parsing stages are not re-executed — the dataset stores pre-processed documents as canonical `ProcessedDocument` JSON.

```
benchmarks/runner.py <benchmark> --dataset <path> [--output <dir>] [--check-regression]
  │
  ▼
BenchmarkRegistry.get(<benchmark>)     → benchmarks/factory.py, benchmarks/registry.py
  │
  ▼
run_document_pipeline() per document   → benchmarks/pipeline/pipeline_runner.py
    Chunking → Embedding (Voyage AI) → Indexing (Qdrant) → Persist Artifacts
  │
  ▼
BenchmarkReportGenerator               → report.json / report.md
  │
  ▼ (if --check-regression)
RegressionDetector.compare(previous, current) → benchmarks/regression/detector.py
    exits non-zero if any metric crosses its threshold
```

## Benchmark suites available

| Suite | Directory |
|---|---|
| Chunking | `benchmarks/chunking/` |
| Embeddings | `benchmarks/embeddings/` |
| Retrieval | `benchmarks/retrieval/` (see `docs/evaluation/retrieval-testing.md`) |
| Reranking | `benchmarks/reranking/` |
| Generation | `benchmarks/generation/` (see `docs/evaluation/metrics.md`) |
| Full ingestion pipeline | `benchmarks/pipeline/` |

## Regression gate

`benchmarks/regression/thresholds.py` defines per-metric thresholds and direction (higher/lower-is-worse). `RegressionDetector` compares `current` vs. the previously stored `report.json`; a candidate present in only one report is skipped (no baseline), not flagged.

## Reports

Persisted under `benchmarks/reports/<suite>/` — `report.json`, `report.md`, and (with `--check-regression`) `regression.json`, `regression_report.md`.

## Not implemented

- Not run in `.github/workflows/ci.yml` — the CI job runs ruff/mypy/pytest only, no benchmark step
- No golden-QA correctness pipeline (see `docs/evaluation/strategy.md`) — this pipeline measures engineering metrics (latency, recall/precision, groundedness proxies), not answer correctness against a human-graded dataset
