# Online Evaluation

**Status:** live (E5, built 2026-08-11; extended by E6, same day). **Source
of truth for implementation detail:**
[`EVALUATION_IMPLEMENTATION_TRACKER.md`](../EVALUATION_IMPLEMENTATION_TRACKER.md)
E5/E6. **Design:** [`EVALUATION_PLAN.md`](../EVALUATION_PLAN.md) §14 (online
evaluation), §15 (offline → online feedback loop). This doc explains how the
online scoring job works conceptually and how it relates to offline
evaluation — for exact code locations, thresholds, and known gaps, see the
tracker entries.

## How online evaluation works (E5)

For every completed Chat/Linear Research/Deep Research generation, two tiers
run:

1. **Free deterministic checks — 100% of traffic, always.** Right now
   that's citation validity (source existence, retrieval provenance,
   fabrication rate — reusing E4's checker). Cheap, no LLM call, so there's
   no reason to sample it.
2. **LLM-judge suite (Ragas: faithfulness, answer_relevancy,
   context_precision/recall) — a risk-weighted sample**, decided by
   `decide_sampling()` in priority order:
   - guardrail-flagged request → always scored
   - Deep Research review decision ≠ `PASS` → always scored
   - inside a config-fingerprint canary window → oversampled
   - otherwise → flat baseline (~7.5%)

The idea (§14 of the eval plan): score 100% of what's already free, save the
expensive LLM calls for traffic that's either already suspicious or a small
representative slice of everything else. Results land in `eval_scores`, one
row per `(generation, metric)`.

**A third signal lands in the same table (E6):** a user's thumbs up/down on
`POST /feedback` is mirrored into `eval_scores` too (`metric_name=
"user_rating"`, `source=human_feedback`), upserted in place if they change
their vote. So `eval_scores` is the single table holding all three signal
types this doc discusses — online-sampled automated scores, human feedback,
and (below) offline benchmark results — not just the online-scoring output
the table name might suggest.

## How online and offline fit together

They're the two halves of one loop, not separate systems — and as of E6,
both write into the same `eval_scores` table, not just conceptually mirrored
processes:

```
Offline (benchmarks/, curated datasets)          Online (E5, live traffic)
──────────────────────────────────────           ──────────────────────────
Golden dataset (115 hand-verified examples)       Real production generations
Ragas scoring + regression gates in CI            Same Ragas scoring, sampled
Blocks a *release* if quality regresses           Scores what's *actually shipped*
Per-example results -> eval_scores (E6)           Every result -> eval_scores (E5)
```

- **Offline asks "is this change safe to ship?"** — runs against a fixed,
  known-correct dataset, gates CI with absolute thresholds (citation
  validity must be 100%, schema validity 100%) and relative regression
  thresholds (faithfulness mustn't drop >2-3% vs. baseline). Until E6, this
  was the CI-smoke-tier lexical benchmark only — the golden dataset's real
  Ragas judge had no runnable driver at all, only a single pytest test using
  a fake judge. `GoldenSetBenchmark` (E6) is that missing driver: it runs a
  live generation call per example through the real judge and, via a
  separate `persist_golden_set_scores.py` step, writes each example's score
  into `eval_scores` too (`source=offline_benchmark`, `dataset_example_id`
  set) — append-only, so each release's run becomes its own trend point
  rather than overwriting the last one.
- **Online asks "is production actually behaving?"** — you can pass every
  offline gate and still regress in the wild (a prompt change that's fine
  on the golden set but breaks on a real user's phrasing), so E5 is the
  check on reality itself, not just on the curated proxy for it.
- **The loop closes through feedback, not yet built (E10):** a confirmed
  real production failure — caught either by E5's online scoring or a
  user's thumbs-down (now itself an `eval_scores` row too, per E6) — gets
  tagged and promoted into the golden dataset. The next release's offline
  CI run then tests against that exact failure, so a real regression never
  recurs silently. **The data half of this loop now exists** (online scores,
  human feedback, and offline results all land in one queryable table); the
  **promotion half** — a human confirming a failure and writing it back into
  `rag_answer_gold` — is still E10, not yet built.

One more connective piece already built: LangSmith ties a trace to its
feedback (E22) and to `eval_scores` (via `generation_id`), so both signals
are inspectable against the same run, not siloed.
