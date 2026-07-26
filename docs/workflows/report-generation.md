# Report Generation Workflow (Deep Research)

**Status:** Implemented — `app/ai/runtime/research/workflows/multi_wave_research.py`, a LangGraph state machine with three human-in-the-loop checkpoints.

---

## Flow

```
prepare_wave → dispatch_wave (parallel Send per task) → retrieve_task → advance_wave
   └── loop until all waves complete ──┘
  │
  ▼
aggregate
  │
  ▼
await_plan_approval  ⏸ (interrupt — checkpoint 1)
  │
  ▼
synthesize            → drafts the report (LLM)
  │
  ▼
review                → ResearchReviewService (see docs/evaluation/report-quality.md)
  │
  ├─ REVISE_SYNTHESIS ──────► prepare_synthesis_revision → synthesize (loop)
  │
  ├─ RESEARCH_GAPS ─────────► prepare_gap_research → retrieve_gap_task → aggregate_gap_evidence
  │                              │
  │                              ├─ needs web search? → evaluate_web_search_need
  │                              │      └─ await_web_search_approval ⏸ (interrupt — checkpoint 2)
  │                              │             └─ search_web_gap → aggregate_gap_evidence
  │                              └─ finalize_gap_limitations → await_report_approval
  │
  ├─ FAIL ──────────────────► fail → END
  │
  └─ PASS / FINALIZE_WITH_LIMITATIONS
        │
        ▼
   await_report_approval ⏸ (interrupt — checkpoint 3)
        │
        ├─ rejected → END (draft/evidence still published as a plain answer, no PDF)
        │
        └─ approved → persist_final_report (PDF) → suggest_related_papers → END
```

## Human-in-the-loop checkpoints

| Checkpoint | Node | Can do |
|---|---|---|
| 1. Plan approval | `await_plan_approval` | Approve/reject the research plan before task execution |
| 2. Web search approval | `await_web_search_approval` | Approve/reject a web-search detour during gap research |
| 3. Report approval | `await_report_approval` | Approve, reject, or submit an `edited_draft` before PDF generation |

Each is a LangGraph `interrupt()` — no side effects run before the call, since LangGraph replays the node body on every resume.

## Key building blocks

| Piece | File |
|---|---|
| Graph definition | `app/ai/runtime/research/workflows/multi_wave_research.py` |
| Review scoring | `app/ai/runtime/research/review.py` |
| PDF generation | `app/ai/runtime/research/reporting/pdf.py` |
| Evidence bundling | `app/ai/runtime/research/evidence.py` |
| Draft model | `app/ai/runtime/research/synthesis/models.py` |

## Rejection behavior

Rejecting the report approval does **not** fail the run — it skips straight to `END`, bypassing only `persist_final_report` (the PDF). The already-synthesized draft and evidence are still available to publish as a plain answer. Rejecting the *plan* approval has no such fallback — there's nothing synthesized yet.

## Related

- `docs/evaluation/report-quality.md` — the review/scoring logic
- ADR-034 (deep-research-product-routing), ADR-036 (web-search-tool-and-approval-checkpoint)
