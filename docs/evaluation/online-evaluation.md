# Online Evaluation

**Status:** live (E5, built 2026-08-11). **Source of truth for implementation
detail:** [`EVALUATION_IMPLEMENTATION_TRACKER.md`](../EVALUATION_IMPLEMENTATION_TRACKER.md)
E5. **Design:** [`EVALUATION_PLAN.md`](../EVALUATION_PLAN.md) §14 (online
evaluation), §15 (offline → online feedback loop). This doc explains how the
online scoring job works conceptually and how it relates to offline
evaluation — for exact code locations, thresholds, and known gaps, see the
tracker entry.

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

## How online and offline fit together

They're the two halves of one loop, not separate systems:

```
Offline (benchmarks/, curated datasets)          Online (E5, live traffic)
──────────────────────────────────────           ──────────────────────────
Golden dataset (115 hand-verified examples)       Real production generations
Ragas scoring + regression gates in CI            Same Ragas scoring, sampled
Blocks a *release* if quality regresses           Scores what's *actually shipped*
```

- **Offline asks "is this change safe to ship?"** — runs against a fixed,
  known-correct dataset, gates CI with absolute thresholds (citation
  validity must be 100%, schema validity 100%) and relative regression
  thresholds (faithfulness mustn't drop >2-3% vs. baseline).
- **Online asks "is production actually behaving?"** — you can pass every
  offline gate and still regress in the wild (a prompt change that's fine
  on the golden set but breaks on a real user's phrasing), so E5 is the
  check on reality itself, not just on the curated proxy for it.
- **The loop closes through feedback, not yet built (E10):** a confirmed
  real production failure — caught either by E5's online scoring or a
  user's thumbs-down — gets tagged and promoted into the golden dataset.
  The next release's offline CI run then tests against that exact failure,
  so a real regression never recurs silently. Right now that promotion step
  doesn't exist yet, so online scoring produces the data but nothing routes
  it back into the golden set automatically.

One more connective piece already built: LangSmith ties a trace to its
feedback (E22) and to `eval_scores` (via `generation_id`), so both signals
are inspectable against the same run, not siloed.
