# Retrieval Testing

**Status:** Implemented as an offline benchmark suite (`benchmarks/retrieval/`). Not wired into CI.

**Related:** ADR-020 (retrieval-evaluation-first-development), `docs/evaluation/metrics.md`.

---

## What's implemented

| Piece | File |
|---|---|
| Benchmark harness | `benchmarks/retrieval/benchmark.py` |
| Golden dataset loader | `benchmarks/retrieval/dataset.py` |
| Test-collection indexer | `benchmarks/retrieval/indexer.py` |
| Metrics (recall@k, precision@k, MRR, NDCG@k) | `benchmarks/retrieval/metrics.py` |
| Metadata-filtering variant | `benchmarks/retrieval/metadata_filtering_benchmark.py` |
| Regression detection | `benchmarks/regression/detector.py`, `thresholds.py` |
| Unit tests | `tests/unit/benchmarks/retrieval/test_metrics.py`, `test_dataset.py`, `test_metadata_filtering_benchmark.py` |

## How to run

```bash
uv run python -m benchmarks.runner retrieval --dataset <path> --output benchmarks/reports [--check-regression]
```

`--check-regression` compares against the previously stored `report.json` in the output directory and exits non-zero if any metric crosses its threshold in `benchmarks/regression/thresholds.py`.

## Flow

1. Load golden dataset (query → relevance-judged filenames)
2. Index the test collection
3. Run each query through the real retrieval stack
4. Score with `recall_at_k` / `precision_at_k` / `reciprocal_rank` / `ndcg_at_k`
5. Write `report.json` / `report.md` to `benchmarks/reports/retrieval/`
6. Optionally diff against the previous report and flag regressions (`regression.json`, `regression_report.md`)

## Not implemented

- Not run in `.github/workflows/ci.yml` (CI only runs ruff/mypy/pytest) — it's a manually-invoked engineering benchmark, not a blocking gate
- No `tests/evaluation/test_retrieval_precision.py` coverage — that file is an empty stub; the real precision/recall logic lives in `benchmarks/`, not `tests/evaluation/`
- No graded relevance judgments (NDCG uses binary relevance only)
