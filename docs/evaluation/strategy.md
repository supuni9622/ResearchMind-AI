# Evaluation Strategy

## Current Status: Superseded

**This document is historical.** It was written when no evaluation logic
existed in this codebase — that's no longer true. The Evaluation Platform
(golden dataset, Ragas scoring, CI regression gates, online scoring,
dashboard, LLM-as-judge, latency SLOs, feedback loop, promotion review,
tool-invocation metrics) has since been built per
[`../PRIORITIZED_ROADMAP.md`](../PRIORITIZED_ROADMAP.md) Wave 0/Wave 1
(items E1–E23), with full task-level detail and code citations in
[`../EVALUATION_IMPLEMENTATION_TRACKER.md`](../EVALUATION_IMPLEMENTATION_TRACKER.md).
Treat those two documents as canonical; the content below describes the
pre-implementation scaffolding state and is kept only as a historical
record of what this doc originally called for.

Do not infer from the directory names below that any of this still runs as
described — several of the "empty" scaffolds referenced (e.g.
`app/ai/quality/`, `api/v1/evaluation.py`) remain intentionally unused, since
the real evaluation logic was built into repo-root `benchmarks/` instead;
see the tracker linked above for where things actually live today.

---

# What's Scaffolded

## RAG quality evaluation — `tests/evaluation/`

Empty test files, one per metric:

- `test_faithfulness.py` — intended to check that generated answers are
  supported by retrieved source documents (no hallucinated claims)
- `test_groundedness.py` — intended to check that citations/claims trace
  back to actual retrieved passages
- `test_retrieval_precision.py` — intended to check that the retriever
  returns relevant chunks for a given query
- `test_reranking.py` — intended to check that the reranker improves
  ordering over raw retrieval

## Security / safety evaluation — `tests/security/`

Empty test files:

- `test_jailbreaks.py` — intended to check the system resists prompt
  jailbreak attempts
- `test_prompt_injection.py` — intended to check the system resists
  injected instructions from untrusted document content or user input

## Application-side scaffolding — `apps/api/app/ai/quality/`

Empty package directories only (`__init__.py`, no logic):

- `ai/quality/evaluation/`
- `ai/quality/benchmarks/`
- `ai/quality/experiments/`
- `ai/quality/regression/`
- `ai/quality/tracing/`
- `ai/quality/telemetry/`
- `ai/registry/evaluators.py` — empty
- `ai/agents/evaluator/` — empty
- `api/v1/evaluation.py` — empty (no evaluation API endpoint exists)

## Documentation scaffolding — `docs/evaluation/`

`README.md`, `benchmarks.md`, `hallucination-testing.md`, `metrics.md`,
`report-quality.md`, `retrieval-testing.md` are all empty placeholders
alongside this file.

---

# Why This Matters Now

The document ingestion pipeline (upload → processing → storage) has real
test coverage — see `docs/guides/testing.md`. Retrieval, generation, and
report-writing (the parts evaluation would actually score) are not built
yet either, based on the current state of `app/ai/`. Evaluation work is
naturally blocked on those existing first; this doc is a marker for when
that changes, not a claim that scoring is happening.

---

# Suggested Next Steps

When retrieval/generation exist and evaluation work starts:

1. Pick a metric library (e.g. RAGAS, DeepEval, or hand-rolled) and record
   the decision as an ADR under `docs/adrs/`, matching the pattern used for
   other infrastructure choices (e.g. `ADR-010-document-processing-strategy.md`).
2. Define a small golden dataset (query, expected retrieved chunks,
   expected answer) checked into the repo so faithfulness/groundedness
   tests are deterministic and reviewable in PRs.
3. Implement one metric end-to-end (retrieval precision is the least
   dependent on generation quality) before building out the rest.
4. Wire results into CI as a non-blocking report first, then promote to a
   blocking gate once the baseline is stable.
