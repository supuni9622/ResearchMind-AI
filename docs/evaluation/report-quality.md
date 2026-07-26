# Report Quality (Deep Research)

**Status:** Implemented — `ResearchReviewService`, wired into the `review` node of the Deep Research graph (`app/ai/runtime/research/workflows/multi_wave_research.py`).

---

## Two-layer review — `app/ai/runtime/research/review.py`

### 1. Deterministic checks — `review_draft()`

Runs first, always. Cheapest-safe-outcome: if it returns `FAIL` or `REVISE_SYNTHESIS`, the model layer is skipped entirely.

| Check | Outcome if failed |
|---|---|
| Citations used in the draft not present in the evidence bundle | `REVISE_SYNTHESIS`, scores `0/0` |
| Evidence has citations but none were used | `REVISE_SYNTHESIS`, scores `0/1` |
| Zero completed research tasks | `FAIL`, scores `0/0` |
| Some tasks failed | `FINALIZE_WITH_LIMITATIONS`, completeness = `completed / (completed + failed)` |
| All checks pass | `PASS`, scores `1/1` |

### 2. Model-assisted review — `ModelReviewAssessment` (bounded)

Only runs if the deterministic layer passed. A schema-constrained LLM call (`response_format=STRUCTURED`, `max_tokens=400`, never cached — `CacheRuntime.REVIEWER`) that can:

- Return a `quality_score` (0–1)
- Request **at most one** additional retrieval question (`gap_questions`, max length 1)
- Raise up to 4 `concerns`

It **cannot** override the deterministic citation/completeness checks or request arbitrary tool work. If the model call fails, the run degrades to the deterministic result with an added limitation — never blocks the report.

## `ResearchReview` decision outcomes

| Decision | Meaning | Routes to |
|---|---|---|
| `PASS` | Clean | report-approval checkpoint |
| `REVISE_SYNTHESIS` | Unsupported/unused citations | back to `synthesize` |
| `RESEARCH_GAPS` | Model found one addressable evidence gap | gap-research sub-flow (retrieval, optionally web search) |
| `FINALIZE_WITH_LIMITATIONS` | Some tasks failed / gaps couldn't be closed | report-approval checkpoint, with limitations listed |
| `FAIL` | No usable evidence at all | run fails |

## Scores tracked per review

- `citation_integrity_score` (0–1)
- `completeness_score` (0–1)
- `model_quality_score` (0–1, optional — only when the model layer ran)

Logged via `research_runtime.graph.review_completed`; each review iteration is persisted as a `ResearchReviewArtifact`.

## Human checkpoint

`review` feeds `await_report_approval` — a LangGraph `interrupt()` where a human approves, rejects, or edits the draft before `persist_final_report` (PDF generation) runs.

## Not implemented

- No standalone automated readability/coherence/style scoring
- No golden-report dataset or regression test suite for report quality
- No `docs/evaluation`-side test coverage — this logic is exercised by `tests/unit/ai/runtime/research/` (workflow/graph tests), not a dedicated evaluation harness
