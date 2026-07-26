# Evaluation Metrics

**Status:** Implemented as offline engineering-benchmark scorers. Not wired into CI as a quality gate.

---

## Retrieval metrics — `benchmarks/retrieval/metrics.py`

Operate on a ranked list of retrieved chunk filenames, collapsed to unique documents by first occurrence, compared against a set of relevance-judged filenames.

| Metric | Function | Meaning |
|---|---|---|
| Recall@k | `recall_at_k()` | Fraction of relevant documents found in top-k |
| Precision@k | `precision_at_k()` | Fraction of top-k retrieved documents that are relevant |
| MRR | `reciprocal_rank()` | `1 / rank` of the first relevant document |
| NDCG@k | `ndcg_at_k()` | Rank-sensitive gain, binary relevance (no graded judgments) |

Unit-tested: `tests/unit/benchmarks/retrieval/test_metrics.py`.

## Generation metrics — `benchmarks/generation/metrics.py`

Deterministic, no-LLM lexical-overlap scorers (same convention as `HallucinationValidator` in production — see `docs/evaluation/hallucination-testing.md`).

| Metric | Function | Meaning |
|---|---|---|
| Groundedness | `groundedness(answer, context)` | Bag-of-words overlap of answer vs. context |
| Faithfulness | `faithfulness(answer, context)` | Fraction of *sentences* individually supported by context (claim-level, not whole-answer average) |
| Relevance | `relevance(answer, query)` | Fraction of query terms addressed in the answer |
| Completeness | `completeness(answer, expected_answer)` | Fraction of a reference answer's key terms present in the generated answer |
| Citation accuracy | `citation_accuracy(...)` | Fraction of expected citation filenames actually referenced |

## Production runtime signal (not a benchmark, but related)

| Metric | Where |
|---|---|
| `researchmind_generation_hallucination_flags_total` | Prometheus counter, fed by `HallucinationValidator` on every live generation |
| `citation_integrity_score`, `completeness_score` | Computed per Deep Research report by `ResearchReviewService` — see `docs/evaluation/report-quality.md` |

## Not implemented

- No LLM-judge metrics (RAGAS, DeepEval, or similar) — everything above is deterministic lexical overlap
- No semantic-similarity scoring (embeddings-based)
- No human evaluation pipeline
- `apps/api/app/ai/quality/evaluation/` — empty package, no application-side metrics service
