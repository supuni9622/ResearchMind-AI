# ResearchMind AI — AI Engineering Architecture Audit

**Original audit:** 2026-07-15
**Re-audited:** 2026-07-17
**Re-audited again:** 2026-07-18 (this revision — evidence re-verified directly against current code and a live test collection run, not carried forward from memory)
**Scope:** `apps/api/app/ai/` (Knowledge Platform + Generation Platform), plus the app-wide infrastructure that supports it (observability, error handling, testing, API wiring).
**Purpose:** Establish an honest, evidence-based baseline of where the platform stands against current AI-engineering practice, and enumerate what's missing so future work can be planned deliberately. This report does not recommend rewriting anything already built — the gaps below are framed as **additions**, not corrections, per the constraint that existing implementations stay as-is.

---

## 0. Re-Audit Delta (2026-07-18)

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

## 0.1 Prior Re-Audit Delta (2026-07-15 → 2026-07-17)

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

- **Knowledge Platform** (`app/ai/knowledge/`, ~14.6k LOC+) — document upload, parsing, chunking, embedding, hybrid retrieval, reranking, context assembly, citations, guardrails, and (as of this cycle) a fully real four-provider compression stage. Still the most mature part of the codebase: real providers, real registries, real Qdrant/Valkey integration, real test coverage. **Still never invoked in production** — see below.
- **Generation Platform** (`app/ai/runtime/generation/`) — five real LLM provider adapters (Groq, OpenAI, Claude, Gemini, Ollama), surrounded by a genuinely complete operational shell: Routing, Runtime Caching, Validation (now with a real policy layer and five runtime contracts), Streaming, and Artifacts are all implemented and wired into `GenerationService`/`StreamingService`. Only most of `observability/`'s finer-grained tracker files remain empty scaffolds.
- **Guardrails Platform** (`app/ai/guardrails/`) — a standalone, platform-wide safety layer (input/retrieval/generation/runtime stages), now **genuinely wired for its input stage into every live chat request** via `GenerationService`. Retrieval and generation-stage checks still don't reach production, for the same reason retrieval itself doesn't (below).
- **Artifacts Platform** (`app/ai/artifacts/`) — new this cycle: a centralized, cross-cutting persistence layer for generation/streaming/conversation runs, live-wired and best-effort, giving the platform its first real audit trail and replay capability.

**The single biggest finding from the original audit — no HTTP path reaches an LLM at all — remains only half true, in exactly the same shape it was on 2026-07-17.** `POST /api/v1/chat/stream` and `/api/v1/chat/ws` are live, authenticated, guardrail-gated on input, artifact-persisted, and genuinely stream a real provider's output back to a caller. **But the path that exists is still chat-only, not RAG.** `chat.py` builds an empty `PromptContext` and never calls retrieval, reranking, `ContextBuilderService`, or (transitively) the retrieval/generation-stage guardrails and the newly-completed compression pipeline. Four consecutive platform-completion cycles (Guardrails, Artifacts, Generation-completion, Compression) have now each added real capability to that dark pipeline without closing the one gap that would light it up. The honest current state, unchanged since the last audit: *ResearchMind can answer a question using an LLM's own knowledge, with an input-safety check and a durable audit trail, but still with no citations, no retrieved context, and no retrieval/generation-stage guardrails* — not yet the "cited, guarded, LLM-generated answer over your documents" the platform is built to deliver.

Beyond the RAG-wiring gap, the platform is still missing most of the "day 2" AI-engineering infrastructure that separates a working prototype from a production LLM system: no tracing/APM, no metrics backend (the metrics *interface* is now used in three places, all still `NoOp`), no evaluation harness, domain exceptions still don't participate in the app's structured-error-response machinery, and there's a live, confirmed logging bug (production logs aren't actually JSON despite the code's own docstring claiming they are). Agentic-flow readiness (LangGraph/MCP) remains 0% started, as originally found — though runtime validation now has typed contracts for planner/reviewer/agent/mcp shapes, ahead of any runtime that would produce output for them to validate.

None of this is a criticism of engineering quality — what's been added since the original audit (Routing, Caching, Validation, Streaming, Guardrails wiring, Artifacts, Compression) is well-structured, consistently typed, composition-rooted, and genuinely tested (1,034 collected tests as of this re-audit, confirmed via a live `pytest --co` run, up from 828). The gap is still one of **breadth of completion and of connecting subsystems that individually work**, not depth of what's been built — and it is now, after four cycles of the same pattern, the report's single most important recurring observation.

---

## 2. Maturity Scorecard

Scale: **0** = nonexistent · **1** = stub/placeholder only · **2** = minimal/partial · **3** = functional but incomplete · **4** = solid, production-leaning · **5** = production-grade with headroom for scale

| Dimension | Score (2026-07-17 → 2026-07-18) | One-line verdict |
|---|:-:|---|
| RAG / retrieval pipeline | 4/5 → **4/5** | Now includes a fully-real 4-provider compression stage (was partially stub); still real hybrid search + reranking; still never invoked in production |
| Data modeling & type safety | 4.5/5 → **4.5/5** | Unchanged — consistent Pydantic `extra="forbid"` + `StrEnum` discipline throughout, including Artifacts and the policy layer |
| Generation provider layer | 4/5 → **4/5** | Unchanged — providers themselves untouched this cycle |
| **End-to-end wiring — generation reachable from API** | 3.5/5 → **4/5** | Input-stage guardrails now genuinely gate every live `/chat/stream`/`/chat/ws` request, and every successful call is now artifact-persisted for audit/replay |
| **End-to-end wiring — retrieval reachable from generation (RAG)** | 1/5 → **1/5** | Unchanged — `chat.py` still hardcodes an empty `PromptContext`; `retrieval.py` still bypasses `ContextBuilderService`. Now the report's single most-repeated finding, unmoved across 4 completion cycles |
| Caching — embeddings | 4/5 → **4/5** | Unchanged |
| Caching — generation | 4/5 → **4/5** | Unchanged — L1/L2/L3 all real; L3 still uncalled |
| Routing (model/provider selection) | 4/5 → **4/5** | Unchanged |
| Observability — structured logging | 2.5/5 → **2.5/5** | Unchanged — production JSON-logging bug reconfirmed present |
| Observability — tracing/APM/metrics | 0.5/5 → **0.5/5** | Unchanged in effect — a third metrics-constants module (`generation.py`) was added, but every recorder is still `NoOpMetricsRecorder`; no real backend exists to observe any of it |
| Cost tracking & token optimization | 3/5 → **3/5** | Unchanged |
| Guardrails | 3/5 (capability) / 0/5 (wired) → **4/5** (capability) **/ 2/5** (wired) | Input-stage guardrails now genuinely run on every live chat request via `GenerationService.stream_generate()` — a real, confirmed change. Retrieval-stage (`ContextBuilderService`) and generation-stage (streaming path) checks still never execute in production |
| Input/output validation | 3.5/5 → **4/5** | New policy layer (`AcceptancePolicy`/`FailFastPolicy`/`RuntimeValidationPolicy`) now drives accept/reject/regenerate instead of hardcoded booleans; 4 more output validators; runtime contracts extended from 1 to 5 runtime types |
| Error handling / resilience | 3/5 → **3/5** | Unchanged — `AppException` inheritance gap for `GenerationError`/`EmbeddingError` persists unchanged |
| Streaming | 4/5 → **4/5** | Unchanged core; now additionally artifact-persisted (events/timeline/metrics) and input-guardrail-gated on every call — real production-behavior improvements, not just internal plumbing |
| Conversation memory | 2.5/5 → **3/5** | Still transcript-flattened at the provider boundary, but now has a real immutable per-turn audit trail (`ConversationTurnArtifact`) distinct from provider-native multi-turn |
| Artifacts & audit trail | *(not scored separately before)* → **3.5/5** | Generation/streaming/conversation artifacts live, best-effort, persisted on every real request; replay services real for generation+streaming; session/research/agent/evaluation built and tested but zero live callers |
| Evaluation & QA | 0/5 → **0/5** | Unchanged — `app/ai/quality/` and `tests/evaluation/`/`tests/security/` reconfirmed 100% empty by direct read |
| Testing | 3.5/5 → **4/5** | 828 → 1,034 collected tests (confirmed via live `pytest --co` run); new coverage for artifacts, guardrails wiring, compression, policy layer; still no CI coverage gate |
| Agentic-flow readiness (LangGraph/MCP/tools/memory) | 0.5/5 → **0.5/5** | Unchanged in substance — runtime validation contracts now exist for planner/reviewer/agent/mcp shapes, but that's validation-layer readiness for output that nothing produces yet; LangGraph/MCP/orchestration/tool-execution-loop still entirely absent |

**Composite: ~2.85/5 — incremental, real progress, concentrated entirely in safety and operational maturity rather than in closing the platform's central gap.** Guardrails moved from "built but unreachable" to "genuinely protecting live traffic for one of its four stages." The Generation Platform's internal completion is now essentially finished (policy layer, five runtime contracts, seven-stage output validation, artifact persistence). But the RAG-wiring gap that both prior audits identified as the single highest-leverage fix in the codebase is, after four consecutive completion cycles building capability around it, exactly where it was on 2026-07-15.

---

## 3. Architecture — What Actually Exists Today

```
                    ┌─────────────────────────────────────────────────┐
                    │              app/api/v1/  (FastAPI)              │
                    │  health ✅  auth ✅  documents ✅                 │
                    │  retrieval ✅ (dense/sparse/hybrid only)          │
                    │  chat ✅ (SSE + WebSocket, NEW — plain LLM only)  │
                    │  evaluation ❌ (0 bytes)                          │
                    └──────┬───────────────────────────┬────────────────┘
                           │ retrieval.py calls         │ chat.py calls
                           │ RetrievalService directly  │ StreamingService
                           │ — bypasses everything      │ directly — builds an
                           │ below                       │ EMPTY PromptContext,
                           ▼                             │ bypasses everything
     ┌──────────────────────────────────────────┐        │ in the left column
     │  Knowledge Platform (~14.6k LOC, real)    │        │
     │                                            │        │
     │  upload → processing/docling → chunking → │        │
     │  embeddings (cached) → indexing (Qdrant)   │        │
     │  → retrieval (dense+sparse+RRF+rerank) →   │        │
     │  ContextBuilderService (dedup → expand →   │        │
     │  merge → compress → GUARDRAILS(mini) →     │        │
     │  CITATIONS → format) → PromptContext        │        │
     │                                            │        │
     │  ⚠ still never called by any live route     │        │
     └───────────────────┬────────────────────────┘        │
                          │ PromptContext is the designed   │
                          │ hand-off point — still nothing  │
                          │ constructs it live               │
                          ▼                                  ▼
     ┌───────────────────────────────────────────────────────────────┐
     │  Generation Platform (app/ai/runtime/generation/)              │
     │                                                                  │
     │  create.py → GenerationRegistry → GenerationService              │
     │    .generate() / .stream_generate()                             │
     │  → GuardrailService.evaluate_input() ✅ NEW — genuinely gates   │
     │    every live call, before routing/provider                    │
     │  → RoutingService (model/provider selection + fallback) ✅       │
     │  → CachingService (L1 exact / L2 semantic / L3 session) ✅       │
     │  → ValidationService (input/output/hallucination/runtime,       │
     │    7-stage output pipeline) ✅ + AcceptancePolicy/FailFastPolicy│
     │    /RuntimeValidationPolicy ✅ NEW govern accept/reject/regen   │
     │  → 5 real provider adapters — retry, tools, cost, streaming ✅   │
     │  → StreamingService → runtime/events/ (StreamEvent) →           │
     │    SSE / WebSocket transports ✅                                 │
     │  → ArtifactWriter ✅ NEW — persists GenerationArtifact/          │
     │    StreamArtifact (request/response/validation/guardrails/      │
     │    routing/cache/metrics.json) best-effort, on every call       │
     │                                                                  │
     │  ⚠ observability/ still empty except token_counter.py +         │
     │    the new (NoOp-backed) GenerationMetricsService                │
     └──────────────────────────────────────────────────────────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │  Guardrails Platform (app/ai/guardrails/) — standalone         │
     │  input/retrieval/generation/runtime stages, Source Trust,      │
     │  policies, scoring, artifacts — real MVP, fully implemented    │
     │                                                                  │
     │  ✅ NEW input-stage: wired into GenerationService, live on      │
     │     every /chat/stream + /chat/ws request                      │
     │  ⚠ retrieval-stage: wired into ContextBuilderService, but      │
     │     ContextBuilderService itself is still never called          │
     │  ⚠ generation-stage (faithfulness/citation/PII): only runs      │
     │     inside non-streaming generate(), which chat.py never calls  │
     └──────────────────────────────────────────────────────────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │  Artifacts Platform (app/ai/artifacts/) — NEW this cycle       │
     │  generation/ streaming/ conversation/ — live, wired, tested    │
     │  replay/ — real for generation + streaming                     │
     │                                                                  │
     │  ⚠ session/ research/ agent/ evaluation/ — built + tested,     │
     │     zero live callers (no /research route, no agent runtime,   │
     │     no session concept distinct from Conversation)              │
     └──────────────────────────────────────────────────────────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │  Conversation Persistence (app/models/conversation.py)         │
     │  Conversation + Message, ConversationService                   │
     │  — real DB-backed multi-turn history, loaded by chat.py        │
     │  ⚠ flattened into a text-prefixed user_prompt at generation     │
     │    time — providers still only build one system+user message  │
     └──────────────────────────────────────────────────────────────┘
```

Both platforms individually reflect a coherent design (composition-root factory functions, registry/provider patterns, interface segregation via ABCs), and that design keeps paying off — Routing/Caching/Validation/Streaming/Guardrails/Artifacts have all now slotted into `GenerationService` cleanly because the seams were designed in from the start. **The problem is no longer "construction stopped before the seams were connected" for Generation's own internals — it's specifically that the seam between Knowledge (retrieval) and Generation remains unconnected**, and it is now the *only* seam of its kind left unclosed, having survived four consecutive completion cycles that each had the opportunity (and, for Guardrails and Compression specifically, a direct structural reason) to close it and didn't.

---

## 4. Detailed Findings by Category

### 4.1 RAG Pipeline — strong, still orchestration-dead, now with a fully-real compression stage

Unchanged from the original audit in every respect that matters: upload, Docling parsing, three chunking strategies, three embedding providers with a real Valkey cache, hybrid retrieval with genuine RRF fusion, two reranking providers, and the full context-assembly pipeline are all real. **New this cycle:** the compression stage — previously part-stub — is now fully implemented across all four providers. `TokenBudgetCompressionProvider` and `EmbeddingCompressionProvider` were already real; `LangChainCompressionProvider` (LangChain `ContextualCompressionRetriever` + `LLMChainExtractor`, extracting only query-relevant spans from each chunk) and `LLMCompressionProvider` (per-chunk summarization via `GenerationService.generate()`, falling back to original content rather than dropping a chunk on failure) went from 1-line stubs (confirmed via `git log --follow`) to real, tested implementations, wired into `ContextBuilderService.build()` behind `settings.enable_langchain_compression`.

None of this changes the pipeline's reachability. `chat.py` still constructs `PromptContext(context="", chunks=[])` rather than calling any of it, and `retrieval.py` still bypasses `ContextBuilderService` entirely, calling `RetrievalService` directly. The original audit's framing — "the entire pipeline is orchestration-dead at the API layer" — is now demonstrated a third and fourth time over: once by `retrieval.py`, once by `chat.py`'s empty `PromptContext`, and now twice more by the retrieval-stage guardrails (§4.6) and the newly-completed compression providers, both of which are real and tested but execute exactly zero times against real traffic.

Still missing, unchanged: no semantic (embedding-similarity) chunking strategy; query-level prompt-injection detection still explicitly deferred; guardrail strategy still hardcoded to `RULE_BASED` with `LLAMA_GUARD`/`NEMO`/`LAKERA` as unimplemented enum values; `vectorstores/artifacts/{builder,models,writer}.py` still empty.

### 4.2 Generation Platform — internal completion is now essentially finished

The five provider adapters are unchanged at their core, but the shell around them, and now its finer-grained internals, are substantially real:

- **Prompt management** (`prompts/`) — unchanged, bridged into `GenerationService.generate_from_template()`.
- **Automatic routing** (`routing/`) — unchanged, implemented and wired.
- **Structured output** (`structured_output/`) — unchanged, implemented.
- **Output validation** (`validation/`) — **now a 7-stage pipeline**, up from 3-4 stages as of 07-17: JSON → Schema → Formatting → Completeness → Consistency → ResponseSize → Citation, plus the pre-existing input and hallucination validators. `formatting_validator.py`/`response_size_validator.py`/`completeness_validator.py`/`consistency_validator.py` are new this cycle; the latter two delegate to the generic `runtime/validators/{completeness,consistency}.py` classes rather than duplicating logic.
- **Runtime validation contracts** — extended from Research-only to five runtime types: `validation/runtime/contracts/{research,planner,reviewer,agent,mcp}.py`, all registered in `validation/create.py`. A new `DependencyValidator` (DFS cycle detection) backs Planner's dependency-graph check; `ConsistencyValidator` was generalized to configurable field names so MCP could reuse it for `tool_outputs`/`tool_references`. Still a no-op in production — nothing sets `GenerationRequest.runtime` because no `/research` (or planner/reviewer/agent/mcp) API exists yet.
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

### 4.6 Guardrails & Safety — now genuinely wired, for one of its four stages

This section's verdict changed materially this cycle, and it's worth being precise about exactly how much. The **Guardrails Platform** (`app/ai/guardrails/`) — input (prompt injection, scope, PII), retrieval (context sanitization, Source Trust, citation integrity), generation (faithfulness, schema enforcement, PII leakage), and runtime (budget, loop detection) stages — was fully built as of 07-17 but had zero callers. As of this audit, confirmed by reading the actual call chain rather than the platform's own tests:

- `GenerationService.__init__` takes a real `guardrail_service: GuardrailService`, wired by `runtime/generation/create.py::create_generation_service()`. `_enforce_input_guardrails()` runs `evaluate_input()` at the top of **both** `generate()` and `stream_generate()`, before routing or any provider call, raising `GuardrailViolationError` on a block.
- `StreamingService` (`streaming/create.py`) wraps that same composed `GenerationService`, and `chat.py` calls `StreamingService.stream_generate()` for every `/chat/stream` and `/chat/ws` request. **This means input-stage guardrails now genuinely run on every live chat request** — the first guardrail stage in this codebase's history to actually execute against real traffic.
- The full generation-stage `evaluate()` (faithfulness, citation integrity, PII leakage) only runs inside non-streaming `generate()`'s `_execute_once()`, after structured-output post-processing — an explicit, documented scope decision (buffering a full streamed response to evaluate it wasn't in scope), not an oversight. Since `chat.py` only ever calls `stream_generate()`, **this stage never runs in production today.**
- `ContextBuilderService` gained an optional `guardrail_platform_service` param (`knowledge/context/create.py`) that runs `evaluate_retrieval()` on raw chunks before dedup/expansion/merge/compression, raising `GuardrailBlockedError` on a block. This closes the wiring gap cleanly — but `ContextBuilderService` itself is still never called by any route (§4.1), so this stage is also still 100% dark in production.

Net effect: guardrail *capability* is unchanged from 07-17 (already a real, broader MVP); guardrail *production coverage* moved from a flat 0 to a genuine 1-of-4 stages live — a real, meaningful improvement, but still gated on the same unclosed retrieval seam for the other 3 stages.

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
