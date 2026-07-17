# ResearchMind AI — AI Engineering Architecture Audit

**Original audit:** 2026-07-15
**Re-audited:** 2026-07-17
**Re-audited again:** 2026-07-18
**Re-audited yet again:** 2026-07-18 (this revision — following the Generation Runtime Platform and Research API Platform; evidence re-verified directly against current code and a live test collection run, not carried forward from memory)
**Scope:** `apps/api/app/ai/` (Knowledge Platform + Generation Platform + Research API Platform), plus the app-wide infrastructure that supports it (observability, error handling, testing, API wiring).
**Purpose:** Establish an honest, evidence-based baseline of where the platform stands against current AI-engineering practice, and enumerate what's missing so future work can be planned deliberately. This report does not recommend rewriting anything already built — the gaps below are framed as **additions**, not corrections, per the constraint that existing implementations stay as-is.

---

## 0. Re-Audit Delta (2026-07-18, this revision)

Two more platforms shipped on top of the 07-18 baseline (§0.1 below): the Generation Runtime Platform and the Research API Platform. The second of these is, by a wide margin, the most consequential change this report has covered across any of its revisions — it directly addresses the single finding this audit has repeated across every prior cycle.

**Generation Runtime Platform** (`apps/api/app/ai/runtime/generation/orchestration/`, per `generation_runtime_platform_prd.md`) — a deliberately thin orchestration layer: `context.py`/`state.py`/`interfaces.py`/`orchestrator.py`/`create.py`, exposing one canonical entrypoint, `execute_generation(request, provider=None) -> GenerationResult` (and `GenerationRuntime.execute()`), plus a new `get_generation_runtime()` FastAPI dependency. Confirmed by direct read of `orchestrator.py`: it does not re-implement or reorder anything — `GenerationService.generate()` already owns the full frozen ordering (input validation → input guardrails → routing → cache → provider execution → structured outputs → generation guardrails → output validation → runtime validation → metrics → artifacts); `GenerationRuntime.execute()` only mints a trace context, delegates to `GenerationService.generate()`, and folds the result back into a `GenerationExecutionState` for logging. 11 new unit tests, all passing. This platform's value isn't new capability, it's a single seam every future runtime caller (Research/Planner/Reviewer/Agent/MCP) can call through instead of each reaching into `GenerationService` directly — and it has exactly one real caller so far (below).

**Research API Platform** (`apps/api/app/ai/research/`, routes in `apps/api/app/api/v1/research.py`, per `research_api_prd.md`) — **this is the finding that changes the report's central thesis.** Every revision of this audit, from the original through 07-18, has identified the same single highest-leverage gap: a fully-real, well-tested retrieval → context-assembly → citation pipeline that no live route ever calls, because `chat.py` hardcodes an empty `PromptContext` and `retrieval.py` bypasses `ContextBuilderService` entirely. **That is no longer true for every route.** Confirmed by direct read of `apps/api/app/ai/research/service.py` and `apps/api/app/api/v1/research.py`:

- Four new, authenticated, owner-scoped routes: `POST /research` (ask a question, get `{research_id, query, answer, citations, sources, duration_ms}`), `POST /research/stream` (SSE), `POST /research/citations` (citation-panel preview, retrieval + context only, no generation, no persistence), `GET /research/{research_id}` (replay a persisted session, 404 via `NotFoundException` if missing or not owned by the caller).
- `ResearchService.research()` (the non-streaming path) genuinely calls `RetrievalService.search_hybrid()` → `ContextBuilderService.build()` → `GenerationRuntime.execute()` → persists a `ResearchSession` row → best-effort persists a `ResearchArtifact`. This is **the first time `ContextBuilderService` has ever been invoked by live code** in this codebase's history — every prior audit flagged it as built, tested, and never called; that is now false for this one route. Because `GenerationRuntime.execute()` calls `GenerationService.generate()` (not `stream_generate()`), `POST /research` also genuinely exercises the **generation-stage** guardrails (faithfulness/citation-integrity/PII-leakage) and the full runtime-validation contract for `RuntimeType.RESEARCH` — both previously 100% dark in production (§0.1/§4.6/§4.10).
- `ResearchService.stream_research()` (the `/research/stream` path) still goes through `StreamingService.stream_generate()` directly, per the PRD's own flow diagram — so it inherits the same input-stage-only guardrail limitation `chat.py` has (§4.6): generation-stage checks don't run on this path, a real, documented trade-off (buffer-then-check wasn't in scope), not an oversight.
- A new Postgres table, `research_sessions` (model + `ResearchRepository` + Alembic migration `37117c83beb2_create_research_sessions_table`), gives the product its first persistent, replayable Q&A history — distinct from and complementary to the Artifacts Platform's own best-effort `ResearchArtifact` (which, per §0.1/§4.11, was previously modeled and tested with zero live callers; it now has one).
- `RuntimeType.RESEARCH` and `ArtifactRuntime.RESEARCH` — both reserved-but-unused enum values as of every prior audit — are now genuinely set on a real `GenerationRequest` and exercised by real traffic for the first time.
- Test suite grew from 1,034 to **1,068 collected** (confirmed via a live `pytest --co` run), the +34 split matching the platforms' own claims (11 + 23) exactly.

**What this does *not* change:** `chat.py` is untouched — it still hardcodes `PromptContext(context="", chunks=[])` and still never calls retrieval or `ContextBuilderService`; `retrieval.py` still bypasses `ContextBuilderService` directly. The P0 finding this report has repeated for four-then-five cycles is therefore not "fixed" so much as **superseded by a more precise one**: ResearchMind now has *two* live user-facing answer routes, and exactly one of them (`/research`) does real, cited, guarded RAG — `/chat` still doesn't. Concretely, a user asking a question via `/chat/stream` still gets an LLM's own knowledge with no citations; the same user asking via `/research` now gets a genuinely retrieved-and-cited answer. See §1, §2, and §5 P0 for how this reframes the rest of the report.

**Net effect on the maturity scorecard:** composite moves from ~2.85/5 to **~3.15/5** — the single largest jump of any revision of this audit, because the fix that landed is exactly the one every prior revision named as highest-leverage. See §2 for the full updated scorecard.

---

## 0.1 Prior Re-Audit Delta (2026-07-17 → 2026-07-18)

One day and five commits have passed since the 2026-07-17 re-audit: `implemented langchain compressor`, `added runtime validation to validation platform`, `modified guardrails platform with integration`, `implemented artifacts platform`, `completed compression platform`. This section is the honest scorecard of what changed, verified directly against current code (not the prior audit's memory of itself).

**Fixed since 2026-07-17:**
- **The Guardrails Platform is no longer completely unwired — it now genuinely gates live traffic, for one of its four stages.** `GenerationService.__init__` takes a real `guardrail_service: GuardrailService`, wired by `runtime/generation/create.py::create_generation_service()`. `_enforce_input_guardrails()` runs at the top of both `generate()` and `stream_generate()`, raising `GuardrailViolationError` on a block. Because `StreamingService` (`streaming/create.py`) wraps that same composed `GenerationService` and `chat.py` calls `StreamingService.stream_generate()`, **every live `/chat/stream` and `/chat/ws` request is now genuinely input-guardrail-checked** — confirmed by reading the call chain, not just the platform's own tests. `ContextBuilderService` also gained an optional `guardrail_platform_service` param (`knowledge/context/create.py`) that runs `evaluate_retrieval()` before dedup/expansion — but this stage still never executes in production, because nothing calls `ContextBuilderService` (see below, unchanged). The full generation-stage `evaluate()` (faithfulness/citation-integrity/PII-leakage) only runs inside non-streaming `generate()`'s `_execute_once()` — an explicit scope decision, not an oversight, since streaming would require buffering a full response to evaluate it. Net: **1 of 4 guardrail stages (input) is now live on the only route real users hit; retrieval and generation-stage guardrails are still effectively unreached in production.**
- **A real, centralized Artifacts Platform now exists** (`app/ai/artifacts/`), replacing what was an empty scaffold as of 07-17. `generation/`, `streaming/`, and `conversation/` artifact types are live and wired: `GenerationService.generate()` persists a full `GenerationArtifact` (request/response/validation/guardrails/routing/cache/**metrics**) after every successful call; `StreamingService` persists a `StreamArtifact` (events/timeline/metrics) on stream completion; `chat.py` persists an immutable `ConversationTurnArtifact` per completed turn plus a one-time `conversation.json` identity record. All three are best-effort (catch-log-never-reraise), matching the Guardrails Platform's own persistence pattern. Replay services (`artifacts/replay/generation.py`, `streaming.py`) are real and can reconstruct a `GenerationResult`/re-emit `StreamEvent`s from persisted artifacts, though no API route exposes them yet. `session/`, `research/`, `agent/`, `evaluation/` artifact types are fully built and unit-tested but have zero live callers — the same "built ahead of the runtime that would call it" shape as every other dormant subsystem in this codebase (no `/research` route, no agent runtime, no session concept distinct from `Conversation`).
- **The Generation Platform's remaining internal gaps are closed.** A real policy layer (`generation/policies/{acceptance,fail_fast,runtime}.py`) now governs accept/reject/regenerate decisions — `AcceptancePolicy`, `FailFastPolicy`, `RuntimeValidationPolicy` are wired into `GenerationService.__init__` and drive `_needs_regeneration` instead of hardcoded booleans (confirmed in `service.py`). Runtime validation contracts, previously Research-only, now cover five runtime types (`validation/runtime/contracts/{research,planner,reviewer,agent,mcp}.py`), all registered in `validation/create.py`. Four more output validators shipped (formatting, response-size, completeness, consistency), bringing the output-validation pipeline to seven stages. `generation/observability/{models,service}.py` — empty as of 07-17 — now hosts a real `GenerationMetricsService` that logs a `generation.metrics.recorded` structured event on every call (new metric-name constants in `infrastructure/metrics/generation.py`); it's unconditionally wired (unlike every other optional collaborator) but still backed by `NoOpMetricsRecorder`, so nothing consumes these events yet.
- **The Compression stage of the RAG pipeline went from partially-stubbed to fully real.** `compression/providers/langchain.py` and `llm.py` were 1-line stubs as of 07-17 (confirmed via `git log --follow`); they're now 300+ line real implementations — `LangChainCompressionProvider` (LangChain `ContextualCompressionRetriever` + `LLMChainExtractor`) and `LLMCompressionProvider` (per-chunk summarization via `GenerationService.generate()`, falls back to original content on failure rather than dropping chunks). Both are wired into `ContextBuilderService.build()` alongside the pre-existing token-budget and embedding-redundancy providers, gated by `settings.enable_langchain_compression`. This is real, tested capability added to a pipeline stage — but, like the rest of `ContextBuilderService`, it has zero live callers (see below).
- **Test suite grew again:** 828 tests (07-17) → **1,034 collected** (989 unit + integration, confirmed via a live `pytest --co` run against `.env.test`), covering the new artifacts platform, guardrails wiring, compression providers, and policy layer.

**Still true (unchanged) since 2026-07-17 — and now the report's central, recurring finding:**
- **`chat.py` still hardcodes `PromptContext(context="", chunks=[])`; `retrieval.py` still calls `RetrievalService` directly, bypassing `ContextBuilderService` entirely.** Confirmed by direct read of both files. This is now the **fourth consecutive platform-completion cycle** — Guardrails, Artifacts, Generation-completion, Compression — that shipped real, well-tested capability *onto* the retrieval → context-assembly → guardrails → citations → compression pipeline, without closing the one seam that would let a real user's request reach any of it. Each cycle's scope decision not to touch chat.py is individually reasonable (it's outside each PRD's stated scope) — but four cycles in, the compounding effect is that the gap between "what's built" and "what a live chat request actually uses" keeps widening rather than narrowing. Concretely: guardrails' retrieval-stage checks, the four compression providers, and the entire hybrid-retrieval+reranking+citation pipeline are all real, tested, and 100% dark in production.
- **`GenerationError`/`EmbeddingError` still inherit from plain `Exception`, not `AppException`** — confirmed unchanged by direct read of both `exceptions.py` files.
- **The production JSON-logging bug is still present**, confirmed by direct read of `core/logging.py` — the production branch still only wraps `ExceptionRenderer()`, `JSONRenderer()` is never referenced.
- **No tracing/APM/real metrics backend.** Notable new wrinkle: the platform now has *three* metrics-constant modules (`infrastructure/metrics/{guardrails,generation}.py`, plus upload's pre-existing one) and a growing set of services that log structured "metrics recorded" events — but every one of them still defaults to `NoOpMetricsRecorder`. The metrics *interface* keeps getting adopted correctly; the one thing that would make any of it observable (Prometheus/OTel/any real backend) still doesn't exist.
- **`app/ai/quality/` and `tests/evaluation/`/`tests/security/` are still 100% empty** — re-confirmed by direct read this cycle (`wc -l` on every file returns 0). Four platform-completion cycles have now shipped without touching this gap.
- **Conversation memory is still transcript-flattened at the provider boundary** — `build_messages()` unchanged, still one system + one user message. What's new is a genuine, separate capability: an immutable per-turn audit trail (`ConversationTurnArtifact`) now exists via the Artifacts Platform, so "what was said" is durably recorded even though "how it's re-sent to the LLM" is still string-flattened.
- **L3 Session Cache** — still implemented, still uncalled; no session concept distinct from `Conversation` exists yet to key it on (confirmed via `SessionArtifact` in the new Artifacts Platform, itself scaffold-only for the same reason).

**Net effect on the maturity scorecard:** composite moves from ~2.7/5 to **~2.85/5**. This cycle's work meaningfully improved the platform's safety posture (input guardrails now genuinely gate every live request) and its operational maturity (real accept/reject/regenerate policy, a real artifact/audit trail, more test coverage) — but the single highest-leverage, most-repeatedly-flagged gap in the whole report did not move, and every other subsystem keeps growing *around* it rather than closing it. See §2 for the full updated scorecard.

---

## 0.2 Prior Re-Audit Delta (2026-07-15 → 2026-07-17)

Two days and several milestones have passed since the original audit (Routing Platform, Runtime Caching Platform, Guardrails Platform, most of the Validation Platform, and — most recently — the Streaming Platform + first-ever HTTP wiring of the Generation Platform). This section is the honest scorecard of what actually changed versus what the original report flagged, verified directly against current code rather than assumed from memory of prior sessions.

**Fixed since the original audit:**
- **Cost tracking** — `estimate_cost()`/`build_statistics()` (`providers/base.py`) now multiply real token counts against catalog pricing; `estimated_cost_usd` is populated on every result, including cache hits.
- **Tool/function calling** — all 5 providers now forward `request.tools` to their SDK call (`openai.py`, `claude.py`, `gemini.py`, `groq.py`, `ollama.py`); the `tool_calling` capability flag is no longer decorative.
- **Retry/backoff for generation providers** — `BaseGenerationProvider._execute_with_retry` (exponential backoff, `config.max_retries`) wraps every provider's `generate()`. `timeout_seconds` reaches the SDK client constructor for 3 of 5 providers (OpenAI, Claude, Groq) — Gemini and Ollama still construct their clients without a timeout, though app-level retry still wraps their calls.
- **`tiktoken` is now actually imported and used** — `observability/token_counter.py`. (Token-*budget enforcement* specifically still uses a deterministic word-count heuristic rather than `tiktoken`, by explicit design — see §4.5.)
- **Routing Platform** — implemented and wired: `GenerationService.generate()`/`stream_generate()` resolve a provider via `RoutingService` when none is given explicitly, with fallback chains.
- **Runtime Caching Platform** — L1/L2/L3 implemented and wired; `metadata["cache"]` is genuinely populated on hits (`hit`, `level`, `tokens_saved`, `cost_saved`), not stuck at `False`/`0`. Streaming requests now participate in caching identically to non-streaming ones (a bypass bug introduced during the caching work, and fixed during the streaming work — see the caching platform's own doc history).
- **Validation Platform** (~65% of its own full PRD scope) — input/output/hallucination validators implemented, registered, and called from `GenerationService._execute_once()`; results land on `GenerationResult.validation`.
- **Streaming Platform** — `runtime/events/` (canonical event protocol) and `generation/streaming/` (SSE + WebSocket transports, cache-aware orchestration) are fully implemented, not empty stubs.
- **The single biggest structural gap — API reachability — is now half-fixed.** `POST /api/v1/chat/stream` and `/api/v1/chat/ws` are live, backed by real `Conversation`/`Message` persistence. A question posed to `/chat/stream` now genuinely reaches an LLM and streams a real answer back. This did not exist at all as of the original audit.
- **Test coverage for `runtime/generation`** — was zero, now 35+ test files across providers/catalog/routing/caching/validation/streaming.

**Still true (unchanged) since the original audit:**
- **`GenerationError`/`EmbeddingError` still inherit from plain `Exception`, not `AppException`** — still fall through to the generic 500 handler with no domain status code.
- **The production JSON-logging bug is still present** — `core/logging.py`'s production branch still only wraps `ExceptionRenderer()`, never calls `JSONRenderer()`. Production logs are plain text, not JSON, despite the docstring's claim.
- **No tracing/APM/metrics** — no OpenTelemetry/Sentry/Prometheus; `runtime/generation/observability/` is still empty except `token_counter.py`; `langsmith_api_key` is still an unused settings field.
- **No LangGraph** — not a dependency; the "agentic half" of the stated vision (RAG + LangGraph + MCP) remains 0% started.
- **`app/ai/quality/`** (benchmarks/evaluation/experiments/regression/telemetry/tracing) is still 100% empty `__init__.py` files. No evaluation harness exists.
- **`vectorstores/artifacts/{builder,models,writer}.py`** are still empty, abandoned scaffolds.
- **The Guardrails Platform (`app/ai/guardrails/`) is still completely unwired** — no import of it exists anywhere outside its own package and tests. `GenerationService`, `StreamingService`, and the new `chat.py` all bypass it entirely.

**New gap this re-audit surfaces that the original couldn't have found (chat.py didn't exist yet):**
- **The new chat endpoint has zero retrieval/RAG wiring.** `chat.py`'s `_build_request()` constructs `GenerationRequest(prompt_context=PromptContext(context="", chunks=[]), ...)` — hardcoded empty. `/chat/stream` and `/chat/ws` are pure LLM passthrough with conversation history, not RAG. The Knowledge Platform's retrieval/reranking/`ContextBuilderService` pipeline — genuinely strong, per §4.1 — is still never invoked by any live route. This is the original audit's P0 finding #2 ("wire `ContextBuilderService` into whatever consumes retrieval results") verbatim, still open, now with a concrete second data point: the new chat endpoint was the opportunity to close it and didn't.
- **Multi-turn conversation history is real (persisted) but not structurally real (not a message array).** `ConversationService.load_history()` returns proper `HumanMessage`/`AIMessage` objects, but `chat.py._format_transcript()` immediately flattens them back into a single text-prefixed `user_prompt` string, because `BaseGenerationProvider.build_messages()` still only ever builds one system + one user message. This is a new, explicitly-documented scope limitation rather than an oversight, but it means "conversation memory" is currently persistence-only, not provider-native multi-turn.

**Net effect on the maturity scorecard:** the composite score moves from ~2.1/5 to **~2.7/5** — real progress on the operational shell (cost, caching, routing, validation, streaming, testing) and on the single most consequential wiring gap (generation ↔ HTTP), but the *harder* wiring gap (retrieval ↔ generation, i.e. actual RAG-in-production) and the observability/evaluation/resilience gaps are untouched. See §2 for the full updated scorecard.

---

## 1. Executive Summary

ResearchMind AI is built as two parallel platforms under `apps/api/app/ai/`, joined by a Generation-adjacent operational shell that has grown substantially since the original audit:

- **Knowledge Platform** (`app/ai/knowledge/`, ~14.6k LOC+) — document upload, parsing, chunking, embedding, hybrid retrieval, reranking, context assembly, citations, guardrails, and a fully real four-provider compression stage. Still the most mature part of the codebase: real providers, real registries, real Qdrant/Valkey integration, real test coverage. **Now genuinely invoked in production — by `/research`, still not by `/chat`** — see below.
- **Generation Platform** (`app/ai/runtime/generation/`) — five real LLM provider adapters (Groq, OpenAI, Claude, Gemini, Ollama), surrounded by a genuinely complete operational shell: Routing, Runtime Caching, Validation (with a real policy layer and five runtime contracts), Streaming, and Artifacts are all implemented and wired into `GenerationService`/`StreamingService`. New this cycle: a **Generation Runtime Platform** (`orchestration/`) gives every future caller one canonical `execute_generation()`/`GenerationRuntime.execute()` entrypoint into all of that. Only most of `observability/`'s finer-grained tracker files remain empty scaffolds.
- **Guardrails Platform** (`app/ai/guardrails/`) — a standalone, platform-wide safety layer (input/retrieval/generation/runtime stages), genuinely wired for its input stage into every live chat request via `GenerationService`, and — new this cycle, via `/research` only — now the **first live route where the retrieval-stage and generation-stage guardrails also execute against real traffic** (§4.6).
- **Artifacts Platform** (`app/ai/artifacts/`) — a centralized, cross-cutting persistence layer for generation/streaming/conversation runs, live-wired and best-effort. New this cycle: the previously scaffold-only Research artifact writer now has its first live caller too.
- **Research API Platform** (`app/ai/research/`) — new this cycle, and the platform that changes this report's central thesis: `POST /research`, `/research/stream`, `/research/citations`, `GET /research/{id}`, backed by a new `research_sessions` table. This is the first route in ResearchMind's history that composes retrieval, context assembly, generation, and persistence into one real, cited answer.

**The single biggest finding every prior revision of this audit has repeated — a fully-real retrieval/context pipeline that no live route calls — is no longer true for every route.** `POST /api/v1/chat/stream` and `/api/v1/chat/ws` remain exactly as before: live, authenticated, input-guardrail-gated, artifact-persisted, chat-only — `chat.py` still builds an empty `PromptContext` and never calls retrieval or `ContextBuilderService`. But `POST /research`, confirmed by direct read of `apps/api/app/ai/research/service.py`, genuinely calls `RetrievalService.search_hybrid()` → `ContextBuilderService.build()` (dedup/expand/merge/compress/cite, plus the retrieval-stage guardrails and the four-provider compression stage — all newly reachable for the first time) → `GenerationRuntime.execute()` → `GenerationService.generate()` (the non-streaming path, so generation-stage guardrails and full runtime validation against `RuntimeType.RESEARCH` also run) → persists a `ResearchSession` row and a best-effort `ResearchArtifact`. The honest current state: *ResearchMind can now answer a question with a genuinely retrieved, cited, guarded-end-to-end answer over a user's own documents — through `/research`.* `/chat` still can't. Five consecutive platform-completion cycles (Guardrails, Artifacts, Generation-completion, Compression, and now Generation Runtime) built capability around the dark pipeline before this one finally lit it up — through a new route built specifically to do so, not through fixing `chat.py` itself.

Beyond the RAG-wiring gap (now half-closed rather than fully open), the platform is still missing most of the "day 2" AI-engineering infrastructure that separates a working prototype from a production LLM system: no tracing/APM, no metrics backend (the metrics *interface* is now used in three places, all still `NoOp`), no evaluation harness, domain exceptions still don't participate in the app's structured-error-response machinery, and there's a live, confirmed logging bug (production logs aren't actually JSON despite the code's own docstring claiming they are). Agentic-flow readiness (LangGraph/MCP) remains 0% started, as originally found — though runtime validation now has typed contracts for planner/reviewer/agent/mcp shapes, and `RuntimeType.RESEARCH`'s contract is, for the first time, actually being exercised by live traffic rather than sitting dormant.

None of this is a criticism of engineering quality — what's been added since the original audit (Routing, Caching, Validation, Streaming, Guardrails wiring, Artifacts, Compression, Generation Runtime, Research API) is well-structured, consistently typed, composition-rooted, and genuinely tested (1,068 collected tests as of this re-audit, confirmed via a live `pytest --co` run, up from 828 at the original audit and 1,034 last cycle). The gap is no longer one of "breadth of completion and connecting subsystems that individually work" for the platform's central seam — that seam is now closed for one live route. What remains is narrower but still real: `/chat` still doesn't do RAG, and most of the "day 2" infrastructure gaps below are unchanged.

---

## 2. Maturity Scorecard

Scale: **0** = nonexistent · **1** = stub/placeholder only · **2** = minimal/partial · **3** = functional but incomplete · **4** = solid, production-leaning · **5** = production-grade with headroom for scale

| Dimension | Score (2026-07-18 → 2026-07-18, this revision) | One-line verdict |
|---|:-:|---|
| RAG / retrieval pipeline | 4/5 → **4/5** | Unchanged in capability (still a fully-real 4-provider compression stage, hybrid search + reranking); reachability is scored separately below and moved a lot |
| Data modeling & type safety | 4.5/5 → **4.5/5** | Unchanged — consistent Pydantic `extra="forbid"` + `StrEnum` discipline throughout, including the new Research API models |
| Generation provider layer | 4/5 → **4/5** | Unchanged — providers themselves untouched this cycle |
| **End-to-end wiring — generation reachable from API** | 4/5 → **4/5** | Unchanged — `/chat/stream`/`/chat/ws` still guardrail-gated on input and artifact-persisted; `/research` now adds a second, independently-wired reachable path |
| **End-to-end wiring — retrieval reachable from generation (RAG)** | 1/5 → **4/5** | The single biggest jump in this report's history. `POST /research` genuinely calls `RetrievalService` → `ContextBuilderService` → `GenerationRuntime` end-to-end — confirmed by direct read of `research/service.py`. Held below 5/5 because `chat.py`/`retrieval.py` are unchanged: only one of the two live answer routes does RAG |
| Caching — embeddings | 4/5 → **4/5** | Unchanged |
| Caching — generation | 4/5 → **4/5** | Unchanged — L1/L2/L3 all real; L3 still uncalled |
| Routing (model/provider selection) | 4/5 → **4/5** | Unchanged; `/research` accepts an optional `routing_strategy` override, exercising the same routing path as `/chat` |
| Observability — structured logging | 2.5/5 → **2.5/5** | Unchanged — production JSON-logging bug reconfirmed present |
| Observability — tracing/APM/metrics | 0.5/5 → **0.5/5** | Unchanged — every recorder is still `NoOpMetricsRecorder`; no real backend exists to observe any of it |
| Cost tracking & token optimization | 3/5 → **3/5** | Unchanged |
| Guardrails | 4/5 (capability) / 2/5 (wired) → **4/5** (capability) **/ 3/5** (wired) | `/research`'s non-streaming path is the **first live route where retrieval-stage and generation-stage guardrails both execute** (via `ContextBuilderService` and `GenerationService.generate()`), not just input-stage. `/research/stream` and `/chat/stream` remain input-stage-only |
| Input/output validation | 4/5 → **4/5** | Unchanged in capability; `RuntimeType.RESEARCH`'s runtime-validation contract is now exercised by real traffic for the first time, not just registered |
| Error handling / resilience | 3/5 → **3/5** | Unchanged — `AppException` inheritance gap for `GenerationError`/`EmbeddingError` persists unchanged |
| Streaming | 4/5 → **4/5** | Unchanged — `/research/stream` reuses `StreamingService.stream_generate()` as-is, no new streaming capability |
| Conversation memory | 3/5 → **3/5** | Unchanged — `/research` has no conversation/multi-turn concept of its own; it persists single Q&A sessions, not a message history |
| Artifacts & audit trail | 3.5/5 → **4/5** | The previously scaffold-only Research artifact writer now has its first live caller (`ResearchService`), best-effort, same catch-log-never-reraise pattern as Generation/Streaming/Conversation. `session/`, `agent/`, `evaluation/` remain zero-caller |
| Evaluation & QA | 0/5 → **0/5** | Unchanged — `app/ai/quality/` and `tests/evaluation/`/`tests/security/` reconfirmed 100% empty by direct read |
| Testing | 4/5 → **4/5** | 1,034 → **1,068 collected tests** (confirmed via live `pytest --co` run); +34 matches the two platforms' own claims (11 + 23) exactly; still no CI coverage gate |
| Agentic-flow readiness (LangGraph/MCP/tools/memory) | 0.5/5 → **0.5/5** | Unchanged in substance — the Research API is explicitly linear (no decomposition/planning/agents, per its own PRD Non-Goals); LangGraph/MCP/orchestration/tool-execution-loop still entirely absent |

**Composite: ~2.85/5 → ~3.15/5 — the single largest jump this report has recorded, because the fix that landed is exactly the one every prior revision named as highest-leverage.** `POST /research` is a new, real, end-to-end RAG route — retrieval, context assembly, generation, guardrails (three of four stages), validation, and persistence all genuinely composed for the first time. The gain is real but bounded: `/chat` is untouched, so the platform now has a live RAG surface and a live non-RAG surface side by side rather than one unified pipeline, and most of the "day 2" gaps (tracing, evaluation, error-handling, the logging bug) are unchanged.

---

## 3. Architecture — What Actually Exists Today

```
                    ┌─────────────────────────────────────────────────┐
                    │              app/api/v1/  (FastAPI)              │
                    │  health ✅  auth ✅  documents ✅                 │
                    │  retrieval ✅ (dense/sparse/hybrid only)          │
                    │  chat ✅ (SSE + WebSocket — plain LLM only)       │
                    │  research ✅ NEW (POST/stream/citations/GET{id}) │
                    │  evaluation ❌ (0 bytes)                          │
                    └──────┬───────────────────┬─────────────┬─────────┘
                           │ retrieval.py       │ chat.py     │ research.py
                           │ calls               │ calls       │ calls
                           │ RetrievalService    │ Streaming   │ ResearchService
                           │ directly — bypasses │ Service     │ NEW — genuinely
                           │ everything below     │ directly —  │ composes
                           ▼                       │ builds an   │ everything below
     ┌──────────────────────────────────────┐      │ EMPTY       │
     │  Knowledge Platform (~14.6k LOC, real)│      │ PromptContext│
     │                                        │      │             │
     │  upload → processing/docling →         │      │             │
     │  chunking → embeddings (cached) →      │      │             │
     │  indexing (Qdrant) → retrieval          │      │             │
     │  (dense+sparse+RRF+rerank) →            │      │             │
     │  ContextBuilderService (dedup →         │      │             │
     │  expand → merge → compress →            │      │             │
     │  GUARDRAILS(mini) → CITATIONS →         │      │             │
     │  format) → PromptContext                │      │             │
     │                                        │      │             │
     │  ✅ NEW: now called live by             │      │             │
     │  ResearchService (research.py) — the    │      │             │
     │  first live caller ever. retrieval.py   │      │             │
     │  and chat.py still bypass it            │      │             │
     └───────────────────┬────────────────────┘      │             │
                          │ PromptContext is the       │             │
                          │ designed hand-off point —  │             │
                          │ now genuinely constructed   │             │
                          │ live, by /research only     │             │
                          ▼                             ▼             ▼
     ┌───────────────────────────────────────────────────────────────┐
     │  Generation Platform (app/ai/runtime/generation/)              │
     │                                                                  │
     │  orchestration/ (GenerationRuntime) ✅ NEW — canonical           │
     │    execute_generation() entrypoint, /research's only caller     │
     │    into everything below; chat.py still calls                   │
     │    StreamingService directly, bypassing this layer               │
     │  → create.py → GenerationRegistry → GenerationService            │
     │    .generate() / .stream_generate()                             │
     │  → GuardrailService.evaluate_input() — genuinely gates every    │
     │    live call, before routing/provider                          │
     │  → RoutingService (model/provider selection + fallback) ✅       │
     │  → CachingService (L1 exact / L2 semantic / L3 session) ✅       │
     │  → ValidationService (input/output/hallucination/runtime,       │
     │    7-stage output pipeline) ✅ + AcceptancePolicy/FailFastPolicy│
     │    /RuntimeValidationPolicy govern accept/reject/regen          │
     │  → 5 real provider adapters — retry, tools, cost, streaming ✅   │
     │  → StreamingService → runtime/events/ (StreamEvent) →           │
     │    SSE / WebSocket transports ✅ — used by /chat/* and           │
     │    /research/stream alike                                        │
     │  → ArtifactWriter — persists GenerationArtifact/                │
     │    StreamArtifact (request/response/validation/guardrails/      │
     │    routing/cache/metrics.json) best-effort, on every call       │
     │                                                                  │
     │  ⚠ observability/ still empty except token_counter.py +         │
     │    the (NoOp-backed) GenerationMetricsService                    │
     └──────────────────────────────────────────────────────────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │  Research API Platform (app/ai/research/) — NEW this cycle    │
     │  ResearchService — composes Retrieval → ContextBuilderService  │
     │  → GenerationRuntime (non-streaming) / StreamingService        │
     │  (streaming) → ResearchRepository → ResearchArtifactWriter     │
     │                                                                  │
     │  ✅ `POST /research`: full stack, incl. generation-stage         │
     │     guardrails + RuntimeType.RESEARCH validation (calls         │
     │     GenerationRuntime → GenerationService.generate())           │
     │  ⚠ `POST /research/stream`: calls StreamingService directly,    │
     │     same input-stage-only guardrail limit as /chat/stream       │
     │  ✅ `research_sessions` Postgres table (model + repository +    │
     │     migration `37117c83beb2`) — first persistent, replayable    │
     │     Q&A history in the product                                  │
     └──────────────────────────────────────────────────────────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │  Guardrails Platform (app/ai/guardrails/) — standalone         │
     │  input/retrieval/generation/runtime stages, Source Trust,      │
     │  policies, scoring, artifacts — real MVP, fully implemented    │
     │                                                                  │
     │  ✅ input-stage: wired into GenerationService, live on every    │
     │     /chat/stream + /chat/ws + /research + /research/stream req  │
     │  ✅ NEW retrieval-stage: wired into ContextBuilderService,      │
     │     and now genuinely live — via /research only                 │
     │  ✅ NEW generation-stage (faithfulness/citation/PII): live on   │
     │     /research (non-streaming) — the first route to ever run    │
     │     this stage in production. Still dark on /chat/stream and    │
     │     /research/stream, both streaming-only                       │
     └──────────────────────────────────────────────────────────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │  Artifacts Platform (app/ai/artifacts/)                        │
     │  generation/ streaming/ conversation/ — live, wired, tested    │
     │  research/ ✅ NEW live caller — ResearchArtifactWriter,         │
     │    best-effort, via ResearchService                            │
     │  replay/ — real for generation + streaming                     │
     │                                                                  │
     │  ⚠ session/ agent/ evaluation/ — built + tested, zero live     │
     │     callers (no agent runtime, no session concept distinct      │
     │     from Conversation)                                           │
     └──────────────────────────────────────────────────────────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │  Conversation Persistence (app/models/conversation.py)         │
     │  Conversation + Message, ConversationService                   │
     │  — real DB-backed multi-turn history, loaded by chat.py        │
     │  ⚠ flattened into a text-prefixed user_prompt at generation     │
     │    time — providers still only build one system+user message  │
     │  (research_sessions, above, is a separate, single-turn store)  │
     └──────────────────────────────────────────────────────────────┘
```

Both platforms individually reflect a coherent design (composition-root factory functions, registry/provider patterns, interface segregation via ABCs), and that design keeps paying off — Routing/Caching/Validation/Streaming/Guardrails/Artifacts/Generation Runtime have all now slotted into `GenerationService` cleanly because the seams were designed in from the start. **The seam between Knowledge (retrieval) and Generation, flagged as unconnected by every prior revision of this report, is now closed for one live route.** `ResearchService` is the proof that closing it required no rework of anything underneath — it composes `RetrievalService`, `ContextBuilderService`, and `GenerationRuntime` exactly as each already existed, per its own PRD's Non-Goals (no new retrieval/context/generation logic). What's left is not a design gap but a coverage gap: `chat.py` and `retrieval.py` are the same two call sites this report has flagged since the original audit, still bypassing everything below them, now standing out more starkly because a sibling route proves the fix was always this simple.

---

## 4. Detailed Findings by Category

### 4.1 RAG Pipeline — strong, and now genuinely reachable — through one of two live answer routes

Unchanged from the original audit in every respect that matters: upload, Docling parsing, three chunking strategies, three embedding providers with a real Valkey cache, hybrid retrieval with genuine RRF fusion, two reranking providers, and the full context-assembly pipeline (including the fully-real, 4-provider compression stage) are all real. **What changed this cycle isn't the pipeline itself, it's that something finally calls it.**

`ResearchService._retrieve_and_build_context()` (`app/ai/research/service.py`), confirmed by direct read, calls `RetrievalService.search_hybrid()` and then `ContextBuilderService.build()` for every `/research`, `/research/stream`, and `/research/citations` request — the first live invocation of `ContextBuilderService` in this codebase's history. That means dedup, parent expansion, adjacent merge, all four compression providers, the retrieval-stage guardrails (§4.6), and citation generation are now genuinely exercised by real traffic, not just by tests.

This is deliberately partial, not a full fix: `chat.py` still constructs `PromptContext(context="", chunks=[])` and never calls any of it, and `retrieval.py` still bypasses `ContextBuilderService` entirely, calling `RetrievalService` directly. The original audit's framing — "the entire pipeline is orchestration-dead at the API layer" — no longer holds without qualification: it's dead at two of three call sites (`retrieval.py`, `chat.py`) and alive at the third (`research.py`).

Still missing, unchanged: no semantic (embedding-similarity) chunking strategy; query-level prompt-injection detection still explicitly deferred; guardrail strategy still hardcoded to `RULE_BASED` with `LLAMA_GUARD`/`NEMO`/`LAKERA` as unimplemented enum values; `vectorstores/artifacts/{builder,models,writer}.py` still empty.

### 4.2 Generation Platform — internal completion finished, now with one canonical entrypoint

The five provider adapters are unchanged at their core, but the shell around them, and now its finer-grained internals, are substantially real:

- **Prompt management** (`prompts/`) — unchanged, bridged into `GenerationService.generate_from_template()`.
- **Automatic routing** (`routing/`) — unchanged, implemented and wired.
- **Structured output** (`structured_output/`) — unchanged, implemented.
- **Output validation** (`validation/`) — **now a 7-stage pipeline**, up from 3-4 stages as of 07-17: JSON → Schema → Formatting → Completeness → Consistency → ResponseSize → Citation, plus the pre-existing input and hallucination validators. `formatting_validator.py`/`response_size_validator.py`/`completeness_validator.py`/`consistency_validator.py` are new this cycle; the latter two delegate to the generic `runtime/validators/{completeness,consistency}.py` classes rather than duplicating logic.
- **Runtime validation contracts** — extended from Research-only to five runtime types: `validation/runtime/contracts/{research,planner,reviewer,agent,mcp}.py`, all registered in `validation/create.py`. A new `DependencyValidator` (DFS cycle detection) backs Planner's dependency-graph check; `ConsistencyValidator` was generalized to configurable field names so MCP could reuse it for `tool_outputs`/`tool_references`. **No longer a no-op for one of the five** — `ResearchService` sets `GenerationRequest.runtime = RuntimeType.RESEARCH` on every `/research` call (§4.10, §4.12), so the Research contract is now genuinely evaluated against live traffic. Planner/Reviewer/Agent/MCP remain dormant, since no runtime yet sets those.
- **Generation Runtime Platform — new this cycle.** `generation/orchestration/{context,state,interfaces,orchestrator,create}.py`, per `generation_runtime_platform_prd.md`: a single canonical `execute_generation(request, provider=None) -> GenerationResult` / `GenerationRuntime.execute()` entrypoint, plus a `get_generation_runtime()` FastAPI dependency. Confirmed by direct read: it adds no new stage and reorders nothing — it mints a trace context, calls `GenerationService.generate()` unchanged, and folds the result into a `GenerationExecutionState` for logging. Its only real caller so far is `ResearchService` (§4.12); `chat.py` still calls `StreamingService`/`GenerationService` directly, not through this layer. 11 new unit tests.
- **Validation Policy Layer — new this cycle.** `generation/policies/{acceptance,fail_fast,runtime}.py`: `AcceptancePolicy` decides Accept/Reject/Regenerate off a `ValidationReport`; `FailFastPolicy` decides whether an input-stage failure should stop execution before the provider call is even made (new `_enforce_fail_fast_input_validation()` pre-flight hook, currently a no-op safety net since every ERROR-severity input check it could catch is already caught earlier — but the ordering hook now exists); `RuntimeValidationPolicy` decides whether a failed runtime contract should also gate regeneration (defaults permissive, since nothing sets `runtime` yet). All three are optional `GenerationService` constructor params defaulting to permissive instances — default behavior is unchanged, but the decision logic is no longer hardcoded booleans.
- **Runtime Metrics Integration — new this cycle.** `observability/{models,service}.py`, empty as of 07-17, now hosts `GenerationMetricsSnapshot` + `GenerationMetricsService`, logging a `generation.metrics.recorded` structured event on every `generate()` call (new constants in `infrastructure/metrics/generation.py`). Unlike every other optional collaborator, this one always defaults to a real instance rather than `None`-skipping — but it's still backed by `NoOpMetricsRecorder`, so the events are logged, not aggregated anywhere.
- **Token-budget enforcement / config timeout gaps** — unchanged from 07-17 (word-count heuristic by design; Gemini/Ollama still don't receive `timeout_seconds`).
- **Streaming** (`streaming/`) — unchanged core; now also artifact-persisted and input-guardrail-gated (see §4.6/§4.11).
- **Artifacts (§3.6 of the completion PRD)** — `GenerationArtifact` gained a required `metrics: GenerationMetricsSnapshot` field, always persisted as `metrics.json` — see §4.11 for the platform itself.

Genuinely still missing in this platform: most of `observability/`'s finer-grained tracker files (`cost_tracker.py`/`token_tracker.py`/`latency_tracker.py`/`metrics_collector.py` remain empty, deliberately — token/cost accounting already lives on `GenerationResult.statistics`, nothing to re-derive from them yet).

### 4.3 Caching — now real above the embedding layer too

Embedding-layer caching is unchanged and still good. **What's new:** the Runtime Caching Platform (L1 exact/L2 semantic/L3 session) is fully implemented and wired into `GenerationService._generate_with_provider` and `StreamingService.stream_generate`. `GenerationStatistics.estimated_cost_usd`/`metadata["cache"]` are genuinely populated on hits — the original audit's specific claim ("`cache_hit` exists, never set `True`") is now false. Streaming requests participate in caching identically to non-streaming ones (an intermediate bypass, introduced when the caching platform first shipped and fixed as part of the streaming work, is now gone). L3 Session Cache remains implemented but uncalled by anything, since no runtime yet keys off a caller-tracked session id the way it expects.

Native provider prompt-caching (Anthropic/OpenAI's own mechanisms, as distinct from this app's own L1/L2/L3) is still not adopted.

### 4.4 Observability — logging bug confirmed still present; tracing/metrics unchanged

`structlog` is still the one real foundation, with request-id propagation via contextvars. **The bug flagged in the original audit is confirmed still live**, verified directly against `core/logging.py` in this re-audit: the production branch is

```python
renderer: Any = (
    structlog.processors.ExceptionRenderer()
    if is_production
    else structlog.dev.ConsoleRenderer()
)
```

`structlog.processors.JSONRenderer()` is never referenced anywhere in the file. If this is accurate in the deployed environment, production logs are not actually structured JSON — this would silently break any log-aggregation pipeline expecting JSON lines, exactly as originally flagged, and it was not addressed by any of the intervening work (Routing/Caching/Validation/Streaming didn't touch `core/logging.py`).

Tracing/APM and metrics are completely unchanged: no OpenTelemetry/Sentry/Datadog/LangSmith/Langfuse integration, `langsmith_api_key` still an unused setting, `runtime/generation/observability/` still empty except `token_counter.py`, and the generic `MetricsRecorder`/`NoOpMetricsRecorder` abstraction under `infrastructure/metrics/` is still never instantiated.

### 4.5 Cost & Token Optimization — largely fixed

The model catalog's pricing data is now genuinely used: `estimate_cost()` multiplies real prompt/completion token counts (extracted from each provider's SDK response) against `cost_per_input_1m`/`cost_per_output_1m`, and this flows into `GenerationStatistics.estimated_cost_usd` on every call — cached or live. There is still no per-user/per-tenant cost aggregation or budget alerting; that would need to be built on top of what now exists, not from scratch.

Token optimization: `tiktoken` is now actually imported and used (`observability/token_counter.py`), closing the "installed but unused" half of the original finding. The other half — pre-flight token-budget enforcement — is implemented (`TokenBudgetValidator`) but deliberately uses a word-count heuristic rather than `tiktoken` itself, a documented trade-off for determinism inside the validator (not a gap so much as a design choice worth being aware of if precise counts ever matter more than determinism). Dynamic cost-based routing (`RoutingStrategy.CHEAPEST`) still has no dedicated strategy profile of its own, unlike the six strategies (planning, summarization, review, validation, coding, research) that do.

### 4.6 Guardrails & Safety — now genuinely wired for three of its four stages, on one route

This section's verdict changes materially again this cycle. The **Guardrails Platform** (`app/ai/guardrails/`) — input (prompt injection, scope, PII), retrieval (context sanitization, Source Trust, citation integrity), generation (faithfulness, schema enforcement, PII leakage), and runtime (budget, loop detection) stages — was fully built as of 07-17 but had zero callers; 07-18 wired its input stage into live chat traffic. As of this revision, confirmed by reading the actual call chain rather than the platform's own tests:

- `GenerationService.__init__` takes a real `guardrail_service: GuardrailService`, wired by `runtime/generation/create.py::create_generation_service()`. `_enforce_input_guardrails()` runs `evaluate_input()` at the top of **both** `generate()` and `stream_generate()`, before routing or any provider call, raising `GuardrailViolationError` on a block — genuinely live on `/chat/stream`, `/chat/ws`, `/research`, and `/research/stream` alike, since all four ultimately call into `GenerationService`.
- `ContextBuilderService`'s `guardrail_platform_service` param (`evaluate_retrieval()` before dedup/expansion/merge/compression) is **now genuinely live for the first time** — `ResearchService` is the first real caller of `ContextBuilderService` (§4.1), so the retrieval-stage guardrails execute on every `/research`, `/research/stream`, and `/research/citations` call. This was flagged as "wired but 100% dark" every prior revision; that's now false for one route.
- The full generation-stage `evaluate()` (faithfulness, citation integrity, PII leakage) only runs inside non-streaming `generate()`'s `_execute_once()`. **`POST /research` is the first route to ever reach this code path in production**, because it calls `GenerationRuntime.execute()` → `GenerationService.generate()` (not `stream_generate()`). `/chat/stream`, `/chat/ws`, and `/research/stream` all only ever call `stream_generate()`, so this stage remains dark on all three of them — a real, documented scope decision (buffering a full streamed response to evaluate it wasn't in scope for either cycle that could have addressed it), not an oversight.

Net effect: guardrail *capability* is unchanged (already a real, broader MVP); guardrail *production coverage* is now genuinely 3-of-4 stages live on `/research` (input, retrieval, generation — only the runtime stage isn't separately exercised here), versus still 1-of-4 on `/chat/stream`/`/chat/ws`/`/research/stream`. The report's framing shifts from "which stages are wired" (now largely answered) to "which routes reach which stages" — a route-level question, not a platform-completeness one.

### 4.7 Validation & Error Handling

**Validation went from substantially fixed to essentially complete.** `GenerationService._execute_once()` runs a 7-stage output pipeline plus input, hallucination, and (when `runtime` is set) runtime-contract validation, all producing a weighted `ValidationReport`. New this cycle: a real **policy layer** (`AcceptancePolicy`/`FailFastPolicy`/`RuntimeValidationPolicy`) now makes the accept/reject/regenerate decision explicitly rather than via hardcoded booleans, and a fail-fast pre-flight hook runs input validation before guardrails/routing/the provider call. This closes essentially all of what §4.7 flagged as remaining in the Validation Platform.

**Error handling is unchanged and still a real gap.** Reconfirmed by direct read this re-audit: `GenerationError` (`runtime/generation/exceptions.py`) and `EmbeddingError` (`knowledge/embeddings/exceptions.py`) both still inherit from plain `Exception`, not `AppException`. Any of these exceptions reaching a route still falls through to the generic catch-all handler and returns an opaque 500 with no domain-specific status code, even though `register_exception_handlers()` already knows how to map `AppException` subclasses properly. This is a cheap, still-open fix that's been consequential (a live route can trigger it) since 07-17 and remains untouched.

**Resilience is unchanged since 07-17.** Retry/backoff remains real for generation providers only; no circuit breakers anywhere; Qdrant/S3 calls still rely on whatever the underlying SDK does natively.

### 4.8 Evaluation & Quality Assurance — completely unchanged, now confirmed across five cycles

Still the starkest gap in the report, re-verified unchanged this re-audit: every file under `app/ai/quality/{benchmarks,evaluation,experiments,regression,telemetry,tracing}/` is a 0-line `__init__.py`, confirmed via direct `wc -l`. `tests/evaluation/*` and `tests/security/*` remain 0-byte scaffolds — five files now exist (`test_retrieval_precision.py`, `test_reranking.py`, `test_groundedness.py`, `test_faithfulness.py`, `test_prompt_injection.py`, `test_jailbreaks.py`), but every one of them is a literal empty file. No golden dataset, no LLM-as-judge scoring, no RAGAS/DeepEval-style automated evaluation, no regression gate. None of the five intervening completion cycles (Routing, Caching, Validation, Streaming, Guardrails, Artifacts, Generation-completion, Compression) touched this area — there is still no way to know whether the Routing Platform's model choices, the Validation Platform's hallucination scores, or the Guardrails Platform's risk scores correlate with anything real.

### 4.9 Testing — grew again, still skewed toward Generation

`apps/api/app/ai/runtime/generation/` test coverage grew further this cycle (artifacts, guardrails-integration wiring, policy layer all gained real test files). Total collected tests across `tests/unit` + `tests/integration`, confirmed via a live `pytest --co` run against `.env.test`: **1,034**, up from 828 at the 07-17 audit (989 of those are `tests/unit` alone). The Knowledge Platform's own coverage grew with the compression providers but is otherwise unchanged in character (real, substantial, unevenly distributed). `documents.py`/`auth.py` route-level coverage and a CI coverage gate remain as originally found — no CI workflow in this repo references a coverage threshold; the only `coverage` reference in the tree is inside a `node_modules` vendor package, unrelated to this codebase's own CI.

### 4.10 Agentic-Flow Readiness — unchanged in substance, one more layer of readiness-without-a-consumer

Tool/function-calling infrastructure at the provider layer is unchanged from 07-17. New this cycle: runtime validation contracts now exist for `planner`/`reviewer`/`agent`/`mcp` shapes (§4.2), which is agent-*adjacent* readiness — but it's validation logic waiting for an agent runtime to produce output worth validating, not an agent runtime itself. Everything else is unchanged: LangGraph still not installed, no agent/planner/orchestrator classes anywhere, no MCP implementation, no tool-execution loop driving the `request.tools` plumbing all 5 providers support, and conversation memory is still flattened into a single-message prompt at the provider boundary (though now backed by a real immutable turn-artifact audit trail — see §4.11).

### 4.11 Artifacts Platform — new, and a genuinely different kind of subsystem than the others

Every other platform added since the original audit (Routing, Caching, Validation, Streaming, Guardrails) sits *in* the generation call path, shaping what happens during a request. The new **Artifacts Platform** (`app/ai/artifacts/`) sits *after* it — a centralized, cross-cutting persistence layer that snapshots what happened, for audit and replay, independent of whether the request itself succeeded fully.

- **Live and wired:** `GenerationService.generate()` persists a `GenerationArtifact` (request/response/validation/guardrails/routing/cache/metrics) after every successful call; `StreamingService` persists a `StreamArtifact` (events/timeline/metrics) on stream completion; `chat.py` persists a `ConversationTurnArtifact` per completed turn (a fresh, never-overwritten object per turn — the platform's immutability principle) plus a one-time `conversation.json` identity record. All three follow the same catch-log-never-reraise pattern the Guardrails Platform's own artifact persistence established — a storage failure can't fail a request that already succeeded.
- **Real replay:** `artifacts/replay/{generation,streaming}.py` can reconstruct a `GenerationResult` or re-emit a `StreamEvent` sequence from persisted artifacts. No API route exposes this yet, but the services themselves are real and tested.
- **Scaffold-only:** `session/`, `research/`, `agent/`, `evaluation/` artifact types are fully modeled, built, and unit-tested (with a fake `DocumentStorage`), but have zero live callers — there's no `/research` route, no agent runtime, and no session concept distinct from `Conversation` for any of them to attach to. This is the same "built ahead of the API surface that would drive it" pattern this codebase has repeated across Runtime Caching's L3, Runtime Validation's contracts, and now Artifacts — a consistent, if slightly concerning, engineering habit of building the platform layer before the thing it serves exists.

---

## 5. Gap Inventory (Prioritized)

Re-prioritized against current reality. Items resolved since 2026-07-17 have been removed from this list entirely (see §0 for what they were); everything below is either still open or newly surfaced.

### P0 — The one thing that would make this an actual RAG product
1. **Wire retrieval + `ContextBuilderService` into `chat.py`.** Still the single highest-leverage gap in the entire codebase, now more so than ever: the hand-off type (`PromptContext`) exists, the pipeline that builds a real one exists and is well-tested (and, this cycle, gained a fully-real compression stage), and the consumer (`StreamingService.stream_generate`) already accepts a `GenerationRequest` carrying it — `chat.py` just needs to call retrieval and `ContextBuilderService` before constructing the request, instead of hardcoding an empty context. Doing this activates **four** dormant subsystems at once: retrieval, `ContextBuilderService`'s retrieval-stage guardrails, citations, and the compression pipeline — up from three at the last audit, since Compression is new this cycle.

### P1 — Needed before this is safe/affordable to run for real users
2. **Make AI-domain exceptions inherit `AppException`** instead of plain `Exception` — still open, still cheap, still consequential since `/chat/stream` is a live path that can surface these exceptions to a real caller as an opaque 500.
3. **Fix the production JSON-logging bug** — add the missing `structlog.processors.JSONRenderer()` call in `core/logging.py`'s production branch; verify against the actual deployed config, since log-aggregation correctness depends on it.
4. **Extend guardrail coverage on the streaming path to the generation stage** — `stream_generate()` currently only runs the input-stage pre-check; faithfulness/citation-integrity/PII-leakage checks only run inside non-streaming `generate()`, which `chat.py` never calls. This would need a design decision (buffer-then-check vs. incremental checking) that was explicitly out of scope for this cycle's PRD.
5. **Timeout plumbing for Gemini and Ollama** — the 2 of 5 providers whose SDK client construction still doesn't receive `config.timeout_seconds`, unchanged since 07-15.

### P2 — Needed to operate this with confidence at scale
6. **Tracing/APM** — pick one of OpenTelemetry, LangSmith, or Langfuse (the `langsmith_api_key` setting still exists, unused, six platforms later) and instrument the generation call path.
7. **A real metrics backend** — three separate metrics-constants modules now exist (upload, guardrails, generation), all defaulting to `NoOpMetricsRecorder`. Standing up Prometheus (or replacing the interface) behind any one of them would immediately make the others useful too, since they share the same `MetricsRecorder` interface.
8. **Evaluation harness** — still the single largest gap in the report by scope: golden Q&A datasets, retrieval-precision and faithfulness/groundedness scoring (test files scaffolded — now six of them — still every one 0 bytes), and a regression gate in CI. More urgent with every cycle, since there are now a Routing Platform making model choices, a Validation Platform scoring hallucinations, and a Guardrails Platform scoring risk, with nothing measuring whether any of the three is actually working.
9. **Per-user/per-tenant cost aggregation and budget alerting**, now that per-request `estimated_cost_usd` is real and available to aggregate.
10. **CI test-coverage gate** — still no CI workflow in this repo references a coverage threshold, despite 1,034 collected tests now existing to gate on.

### P3 — Roadmap items (agentic flows + RAG-adjacent polish), from scratch or near-scratch
11. **A real multi-message provider API** — `build_messages()` still only ever emits one system + one user message; this is what's actually blocking conversation history from being provider-native instead of transcript-flattened.
12. **LangGraph adoption** — still not installed; needed before any real orchestration (multi-step retrieve→generate→verify, or agentic tool use) is possible on top of the tool-calling plumbing and the new planner/reviewer/agent/mcp runtime-validation contracts.
13. **A tool-execution loop** that actually drives the `request.tools` plumbing all 5 providers support.
14. **MCP** — still zero code, per the roadmap docs' Phase 6 plan.
15. **Streaming rate limiting / per-user concurrent-stream cap** — called out in the Streaming Platform's own "Production Considerations" section as a known gap, unchanged.
16. **L3 Session Cache and Session Artifacts wiring** — both implemented, still nothing calls either, since no session concept distinct from `Conversation` exists yet.
17. **Native provider prompt-caching** (Anthropic/OpenAI) — distinct from and complementary to this app's own L1/L2/L3.
18. **An API surface for Artifact replay** — `GenerationReplayService`/`StreamReplayService` are real and tested but have no route exposing them.

---

## 6. What's Already Good (worth preserving as-is)

Everything from prior audits' lists still holds, plus what's been added since:

- The **composition-root pattern** (`create_*()` factory functions building registries from `settings`) is consistent across every platform added since the original audit, now including Artifacts and the policy layer — this discipline has now absorbed eight platforms cleanly without architectural strain.
- **Pydantic discipline** (`extra="forbid"`, `StrEnum`, frozen configs) is applied consistently in all new code, including the Artifacts Platform's dozen-plus new models.
- **Hybrid retrieval with real RRF fusion + reranking, now paired with a fully-real 4-provider compression stage** — still more sophisticated than what many production RAG systems ship with initially, and still waiting for a consumer.
- **The fail-open / best-effort persistence pattern keeps getting reused correctly.** First seen in the embedding cache, then the Runtime Caching Platform's L1/L2/L3, now a third time in the Artifacts Platform (`GenerationArtifact`/`StreamArtifact`/`ConversationTurnArtifact` writes are all catch-log-never-reraise) — a storage failure can't fail a request that already succeeded, applied consistently across three independently-built subsystems rather than reinvented each time.
- **The Guardrails integration correctly distinguished "stateless, safe to re-run" from "needs new state."** Input guardrails are deliberately re-evaluated inside the full `evaluate()` call (to re-check a regeneration attempt's corrected prompt) rather than being treated as already-done — a subtle correctness call that's easy to get wrong in either direction.
- **Structured logging conventions** (`structlog.get_logger()`, dot-namespaced events, kwargs-not-f-strings) remain consistent across every new platform, including new `generation.started`/`provider.started`/`validation.started` events added this cycle — the one real observability convention this codebase has keeps being followed correctly, even as the JSON-rendering bug around it goes unfixed.

---

## 7. Bottom Line

ResearchMind AI spent this cycle on safety and operational maturity rather than on its central open question, and it's worth being clear-eyed about that trade-off. Input-stage guardrails now genuinely protect every live chat request — a real, first-of-its-kind production safety win. The Generation Platform's own internal completion is now essentially finished: a real accept/reject/regenerate policy layer, validation contracts for five runtime types, a seven-stage output-validation pipeline, and a genuine artifact/audit trail on every request. None of this is small, and the composition-root architecture keeps proving itself by absorbing new platforms — Guardrails wiring, Artifacts, Compression, the policy layer — without strain.

But the problem both prior audits identified as the platform's single highest-leverage gap — **the seam between retrieval and generation** — did not move at all this cycle, for the fourth cycle in a row. Every other seam of its kind in this codebase has now been closed: Routing↔Generation, Caching↔Generation, Validation↔Generation, Streaming↔Generation, Guardrails↔Generation (partially), Artifacts↔Generation. Retrieval↔Generation is now the *only* one left, and it is uniquely surrounded by capability that was built specifically to plug into it and doesn't: `ContextBuilderService`'s retrieval-stage guardrails, its citation pipeline, and now its fully-completed compression stage are all real, tested, and waiting for a caller that doesn't exist. Closing it (§5, P0 #1) remains the single highest-leverage change available in the codebase — every dependency it needs already exists and is already tested. Everything else on this list — tracing, evaluation, the `AppException` gap, the logging bug, generation-stage guardrails on the streaming path — matters, but none of it changes whether a user gets a cited, grounded answer instead of a raw LLM guess, which is still, after five platform-completion cycles, the one thing this platform doesn't yet do end-to-end.
