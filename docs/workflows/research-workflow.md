# Research Workflow

**Status:** Implemented. Two distinct research surfaces, plus an explicit-consent escalation path from one to the other.

**Related:** `docs/workflows/report-generation.md` (Deep Research's internal graph — this doc covers the surface/API level, that one covers the graph internals).

---

## Two surfaces

| | Linear Research | Deep Research |
|---|---|---|
| Entry point | `POST /research`, `/research/stream` | `POST /research/proposals` → approve → worker-executed |
| Service | `ResearchService.research()` / `.stream_research()` | `ResearchProposalService` + `multi_wave_research` graph |
| Execution | Synchronous, single retrieval + generation pass | Asynchronous, multi-wave, dedicated worker (`apps/worker/research_runtime_worker.py`) |
| Human checkpoints | None | 3 (plan / web-search / report — see `report-generation.md`) |
| Cost | One retrieval + one generation call | Planner call + N task calls + synthesis + review, potentially web search |

## Linear Research flow — `ResearchService.research()`

```
get-or-create conversation
  → load conversation history
  → retrieve memory context (session/semantic/research, optional)
  → retrieve + build context (RetrievalService + ContextBuilderService)
  → generate (Generation Runtime, cache_runtime=RESEARCH)
  → persist session + artifact
  → extract + store new memories (best-effort)
```

Same flow backs both `POST /research` (returns full answer) and `POST /research/stream` (SSE) — `StreamingService` wraps the identical generation step.

## Escalation: Linear → Deep Research

Never automatic — always explicit user consent.

```
POST /research/escalation-check
  → ResearchProposalService.check_escalation()
  → runs the same (uncached) planner call as a real proposal
  → ResearchComplexity.SIMPLE → suggested=false
  → multi-step complexity → suggested=true, deterministic reason, proposal persisted

POST /research/proposals            → propose a bounded Deep Research plan (no run started yet)
POST /research/proposals/{id}/approve → authorizes exactly one run; worker executes it later
```

`_escalation_reason()` is deterministic, derived from the plan's own fields (task count / complexity) — never freeform LLM text, so it can't drift or be prompt-injected.

## Rate limits (per owner, Valkey-backed)

| Bucket | Scope | Shared by |
|---|---|---|
| `research` | Linear Research | `/research`, `/research/stream`, `/research/citations` (same retrieval/generation cost pool) |
| `deep_research_proposal` | Proposal creation | `/research/proposals`, `/research/escalation-check` (both run the planner call) |
| `deep_research_approval` | Run approval | `/research/proposals/{id}/approve` — the most expensive action in the product |

## Endpoint map — `app/api/v1/research.py`

| Endpoint | Surface | Purpose |
|---|---|---|
| `POST /research` | Linear | Full answer, non-streaming |
| `POST /research/stream` | Linear | SSE streaming answer |
| `POST /research/citations` | Linear | Citations only, no generation |
| `GET /research/{id}` | Linear | Fetch a past research result |
| `GET /research/conversations` / `/{id}` | Linear | Conversation threading, history |
| `GET /research/conversations/{id}/cost` | Linear | Per-conversation usage cost summary |
| `POST /research/proposals` | Deep | Create a bounded plan proposal |
| `POST /research/escalation-check` | Deep | Suggest Deep Research without committing |
| `POST /research/proposals/{id}/approve` | Deep | Authorize a run |
| `GET /research/runs/{id}` | Deep | Run status |
| `POST /research/runs/{id}/cancel` | Deep | Cancel an in-flight run |
| `GET`/`POST /research/runs/{id}/plan` | Deep | Inspect / decide the plan-approval checkpoint |
| `GET`/`POST /research/runs/{id}/web-search` | Deep | Inspect / decide the web-search-approval checkpoint |
| `GET /research/runs/{id}/draft` | Deep | Inspect the pending draft + review summary |
| `POST /research/runs/{id}/report` | Deep | Decide the report-approval checkpoint |
| `GET /research/runs/{id}/events` | Deep | SSE stream of run events |
| `GET /research/runs/{id}/report/download` | Deep | Download the final PDF |

## Not implemented

- No automatic escalation — a Deep Research run is never started without an explicit `/approve` call
- Linear Research has no multi-step planning, review, or human-approval checkpoints (that's what Deep Research adds)
