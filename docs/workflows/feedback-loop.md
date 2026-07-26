# Feedback Loop

**Status:** Partially implemented — automated/system feedback loops exist; no user-facing feedback (thumbs up/down, ratings) exists yet.

---

## 1. Guardrail-driven regeneration

The only closed-loop "detect problem → automatically retry" mechanism in the app.

```
GenerationResult
  │
  ▼
HallucinationValidator.validate()   → groundedness score
  │
  ▼
FaithfulnessGuardrail.check()       → re-scores at FAITHFULNESS_THRESHOLD, issues ERROR
  │
  ▼
GuardrailService                    → RegenerationPolicy.regenerate_on_hallucination
  │
  ▼
GuardrailAction.REGENERATE          → generation re-run
```

Same pattern applies to schema-validation failures via `regenerate_on_schema_failure`. See `docs/evaluation/hallucination-testing.md`.

## 2. Benchmark regression feedback

```
New benchmark run (benchmarks/runner.py --check-regression)
  │
  ▼
RegressionDetector.compare(previous report, current report)
  │
  ▼
Threshold breach → non-zero exit code → surfaces before a regressed change is promoted
```

See `docs/workflows/evaluation-pipeline.md`.

## 3. System-metrics-as-LangSmith-feedback

Not user feedback — `LangSmithMetricsRecorder` (`app/ai/observability/providers/langsmith/recorder.py`) forwards duration/count metrics into LangSmith's `create_feedback()` API, attached to the active trace via a `ContextVar`, so trace-level metrics are visible alongside the run in LangSmith. Best-effort; skipped silently if no active run.

## Deep Research review loop (adjacent, not a "feedback loop" per se)

The `RESEARCH_GAPS` / `REVISE_SYNTHESIS` decisions from `ResearchReviewService` route the graph back to `synthesize` or into a gap-research sub-flow — see `docs/evaluation/report-quality.md` and `docs/workflows/report-generation.md`.

## Not implemented

- No user-facing rating/thumbs-up-down endpoint or schema
- No RLHF or preference-learning loop
- No mechanism feeding user reactions back into memory, routing, or ranking
