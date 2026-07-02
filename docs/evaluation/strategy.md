# Evaluation Strategy

## Current Status: Not Implemented

There is no evaluation logic in this codebase yet. This document exists to
record what's scaffolded so far and what each placeholder is meant to hold,
so the next implementation work has a clear target instead of starting from
nothing.

Do not infer from the directory names below that any of this runs today —
every file listed is either empty or contains only an `__init__.py`.

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
