# ResearchMind AI — AI Engineering Architecture Audit

**Original audit:** 2026-07-15
**Re-audited:** 2026-07-17 (this revision — evidence re-verified against current code, not carried forward from memory)
**Scope:** `apps/api/app/ai/` (Knowledge Platform + Generation Platform), plus the app-wide infrastructure that supports it (observability, error handling, testing, API wiring).
**Purpose:** Establish an honest, evidence-based baseline of where the platform stands against current AI-engineering practice, and enumerate what's missing so future work can be planned deliberately. This report does not recommend rewriting anything already built — the gaps below are framed as **additions**, not corrections, per the constraint that existing implementations stay as-is.

---

## 0. Re-Audit Delta (2026-07-17)

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

- **Knowledge Platform** (`app/ai/knowledge/`, ~14.6k LOC) — document upload, parsing, chunking, embedding, hybrid retrieval, reranking, context assembly, citations, and guardrails. Still the most mature part of the codebase: real providers, real registries, real Qdrant/Valkey integration, real test coverage. **Unchanged in scope since 2026-07-15, and still never invoked in production** — see below.
- **Generation Platform** (`app/ai/runtime/generation/`) — five real LLM provider adapters (Groq, OpenAI, Claude, Gemini, Ollama), now genuinely surrounded by a working operational shell: Routing, Runtime Caching, Validation, and Streaming platforms are all implemented and wired into `GenerationService`/`StreamingService`. Only `artifacts/` and most of `observability/` remain empty stubs.
- **Guardrails Platform** (`app/ai/guardrails/`) — a standalone, platform-wide safety layer (input/retrieval/generation/runtime stages) built to a real MVP standard, but — like the Knowledge Platform — never called from anywhere that executes in production.

**The single biggest finding from the original audit — no HTTP path reaches an LLM at all — is now only half true.** `POST /api/v1/chat/stream` (SSE) and `/api/v1/chat/ws` (WebSocket) are live, authenticated, backed by real `Conversation`/`Message` persistence, and genuinely stream a real provider's output back to a caller. **But the path that exists is chat-only, not RAG.** `chat.py` builds an empty `PromptContext` and never calls retrieval, reranking, or `ContextBuilderService` — the exact pipeline the original audit called "genuinely strong" (§4.1) is still orchestration-dead. So the honest current state is: *ResearchMind can now answer a question using an LLM's own knowledge, with no citations, no retrieved context, and no guardrails* — which is a real product capability that didn't exist two days ago, but it is not yet the "cited, guarded, LLM-generated answer over your documents" the platform is actually built to deliver.

Beyond the RAG-wiring gap, the platform is still missing most of the "day 2" AI-engineering infrastructure that separates a working prototype from a production LLM system: no tracing/APM, no metrics beyond token counting, no evaluation harness, domain exceptions still don't participate in the app's structured-error-response machinery, and there's a live, confirmed logging bug (production logs aren't actually JSON despite the code's own docstring claiming they are). Agentic-flow readiness (LangGraph/MCP) remains 0% started, as originally found.

None of this is a criticism of engineering quality — what's been added since the original audit (Routing, Caching, Validation, Streaming, Guardrails, Conversation persistence) is well-structured, consistently typed, composition-rooted, and genuinely tested (828 passing tests as of this re-audit, up from the prior session's count). The gap is still one of **breadth of completion and of connecting subsystems that individually work**, not depth of what's been built.

---

## 2. Maturity Scorecard

Scale: **0** = nonexistent · **1** = stub/placeholder only · **2** = minimal/partial · **3** = functional but incomplete · **4** = solid, production-leaning · **5** = production-grade with headroom for scale

| Dimension | Score (2026-07-15 → 2026-07-17) | One-line verdict |
|---|:-:|---|
| RAG / retrieval pipeline | 4/5 → **4/5** | Unchanged — real hybrid (dense+sparse+RRF) search, reranking, context compression; still never invoked in production |
| Data modeling & type safety | 4.5/5 → **4.5/5** | Unchanged — consistent Pydantic `extra="forbid"` + `StrEnum` discipline throughout, including all new platforms |
| Generation provider layer | 3/5 → **4/5** | Real retry/backoff, tool-calling, streaming, and cost accounting now exist; timeout still not passed to 2/5 SDK clients |
| **End-to-end wiring — generation reachable from API** | 1/5 → **3.5/5** | `/chat/stream` + `/chat/ws` genuinely work end-to-end for plain LLM chat with real persistence |
| **End-to-end wiring — retrieval reachable from generation (RAG)** | *(not scored separately before)* → **1/5** | Chat bypasses retrieval/`ContextBuilderService` entirely; this is the harder half of the original "1/5" finding and it's still unmet |
| Caching — embeddings | 4/5 → **4/5** | Unchanged — real Valkey-backed cache, fail-open, TTL, null-object pattern |
| Caching — generation | 0/5 → **4/5** | L1 exact (Valkey) + L2 semantic (LangChain `RedisSemanticCache`) + L3 session (implemented, unused) all real; `cache_hit`/`estimated_cost_usd` genuinely populated |
| Routing (model/provider selection) | 0/5 → **4/5** | Scored 12-model catalog, task-based strategies, fallback chains, wired into `generate()`/`stream_generate()` |
| Observability — structured logging | 3/5 → **2.5/5** | Confirmed bug persists: production never actually renders JSON, despite the docstring claiming it does |
| Observability — tracing/APM/metrics | 0.5/5 → **0.5/5** | Unchanged — no OTel/Sentry/Prometheus; `langsmith_api_key` still unused |
| Cost tracking & token optimization | 0.5/5 → **3/5** | Real per-request cost now computed and cache-aware; still no per-user/tenant aggregation or budget alerting |
| Guardrails | 2/5 → **3/5** (capability) **/ 0/5** (wired) | A real, broader MVP platform exists (input/retrieval/generation/runtime stages, Source Trust) but is completely unwired — worse *effective* coverage than the original narrower-but-at-least-reachable-in-theory finding, since nothing calls it at all |
| Input/output validation | 1.5/5 → **3.5/5** | Real multi-stage Validation Platform (input/output/hallucination), wired into `GenerationService`, weighted scoring |
| Error handling / resilience | 2/5 → **3/5** | Retry/backoff now real for generation providers; `AppException` inheritance gap for AI-domain exceptions persists unchanged |
| Streaming | 0/5 → **4/5** | Canonical event protocol + SSE/WebSocket transports, cache-hit replay, heartbeats/timeout ceiling; no rate limiting yet |
| Conversation memory | 0/5 → **2.5/5** | Real persistence and history loading now exist; still transcript-flattened, not a native multi-message API |
| Evaluation & QA | 0/5 → **0/5** | Unchanged — `app/ai/quality/` is still 100% empty scaffolding |
| Testing | 2.5/5 (skewed) → **3.5/5** | `runtime/generation` went from 0 test files to 35+; Knowledge Platform coverage unchanged; still no coverage gate in CI |
| Agentic-flow readiness (LangGraph/MCP/tools/memory) | 0/5 → **0.5/5** | Tool-calling now reaches the SDK layer (real, if unused by any agent); LangGraph/MCP/orchestration still entirely absent |

**Composite: ~2.7/5 — prototype-to-production transition, further along than 2026-07-15's ~2.1/5.** The operational shell around Generation (cost, caching, routing, validation, streaming) has gone from mostly-empty scaffolding to genuinely implemented and tested. The two hardest problems — connecting retrieval to generation in a live request path, and the observability/evaluation/resilience gaps that make an LLM system safe to operate — are exactly where they were two days ago.

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
     │  → RoutingService (model/provider selection + fallback) ✅       │
     │  → CachingService (L1 exact / L2 semantic / L3 session) ✅       │
     │  → ValidationService (input/output/hallucination) ✅             │
     │  → 5 real provider adapters — retry, tools, cost, streaming ✅   │
     │  → StreamingService → runtime/events/ (StreamEvent) →           │
     │    SSE / WebSocket transports ✅ NEW                             │
     │                                                                  │
     │  ⚠ artifacts/ still empty; observability/ still empty except   │
     │    token_counter.py                                              │
     └──────────────────────────────────────────────────────────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │  Guardrails Platform (app/ai/guardrails/) — standalone         │
     │  input/retrieval/generation/runtime stages, Source Trust,      │
     │  policies, scoring, artifacts — real MVP, fully implemented    │
     │                                                                  │
     │  ⚠ zero callers anywhere — GenerationService, StreamingService,│
     │    and chat.py all bypass it entirely                          │
     └──────────────────────────────────────────────────────────────┘

     ┌──────────────────────────────────────────────────────────────┐
     │  Conversation Persistence (app/models/conversation.py, new)    │
     │  Conversation + Message, ConversationService                   │
     │  — real DB-backed multi-turn history, loaded by chat.py        │
     │  ⚠ flattened into a text-prefixed user_prompt at generation     │
     │    time — providers still only build one system+user message  │
     └──────────────────────────────────────────────────────────────┘
```

Both platforms individually reflect a coherent design (composition-root factory functions, registry/provider patterns, interface segregation via ABCs), and that design has now visibly paid off — the Routing/Caching/Validation/Streaming/Guardrails platforms all slotted into `GenerationService` cleanly because the seams were designed in from the start. **The problem is no longer "construction stopped before the seams were connected" for Generation's own internals — it's specifically that the seam between Knowledge (retrieval) and Generation, and between Guardrails and Generation, remain unconnected**, even though a brand-new consumer (`chat.py`) was just built and had every opportunity to close at least the retrieval seam.

---

## 4. Detailed Findings by Category

### 4.1 RAG Pipeline — strong, still orchestration-dead

Unchanged from the original audit in every respect that matters: upload, Docling parsing, three chunking strategies, three embedding providers with a real Valkey cache, hybrid retrieval with genuine RRF fusion, two reranking providers, and the full context-assembly pipeline are all real. **What's changed is that there is now a second, independent piece of evidence that this pipeline is disconnected from production**: the new `chat.py` was built this week and constructs `PromptContext(context="", chunks=[])` rather than calling any of it. The original audit's framing — "the entire pipeline is orchestration-dead at the API layer" — is not just still true, it's now demonstrated twice (once by `retrieval.py` returning raw chunks with no context assembly, once by `chat.py` doing generation with no retrieval at all).

Still missing, unchanged: no semantic (embedding-similarity) chunking strategy; query-level prompt-injection detection still explicitly deferred; guardrail strategy still hardcoded to `RULE_BASED` with `LLAMA_GUARD`/`NEMO`/`LAKERA` as unimplemented enum values; `vectorstores/artifacts/{builder,models,writer}.py` still empty.

### 4.2 Generation Platform — now has a real operational shell

The five provider adapters are unchanged at their core, but the shell around them has gone from "~75 empty stub files" to substantially real:

- **Prompt management** (`prompts/`) — still pre-existing (not built this cycle), but now genuinely bridged into `GenerationService.generate_from_template()`.
- **Automatic routing** (`routing/`) — **implemented.** A scored 12-model catalog, capability/policy filtering, 15 task-based `RoutingStrategy` values, distinct-provider-preferred fallback chains. `generate()`/`stream_generate()` both resolve a provider via routing when none is given explicitly.
- **Structured output** (`structured_output/`) — implemented in an earlier cycle (native schema-constrained decoding for all 5 providers, parser/repair fallback) — the original audit predates this too but it's confirmed real now.
- **Output validation** (`validation/`) — **implemented**, ~65% of its full target scope: input (empty-prompt, token-budget, provider-limits, context) and output (schema, JSON, citation) validators, plus a hallucination validator, all wired into `GenerationService._execute_once()` via `ValidationService`.
- **Token-budget enforcement** — implemented as `TokenBudgetValidator`, using a deterministic word-count heuristic (not `tiktoken`) by explicit design, to keep validation itself deterministic and free of live API calls. `tiktoken` itself is now used elsewhere (`observability/token_counter.py`).
- **Config fields with no effect** — `BaseGenerationConfig.timeout_seconds` now reaches `AsyncOpenAI`/`AsyncAnthropic`/`AsyncGroq` client construction. It still does **not** reach Gemini's `genai.Client(api_key=...)` or Ollama's `AsyncClient(host=...)` — a smaller, partial version of the original finding.
- **Streaming** (`streaming/`) — **implemented** this cycle: `StreamingService`, SSE transport (heartbeat, timeout ceiling), WebSocket transport, cache-hit replay as synthetic token events.

Genuinely still missing: `artifacts/` (empty), and most of `observability/` (only `token_counter.py` is real).

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

### 4.6 Guardrails & Safety — a real platform now exists, and it's more disconnected than before

This is the one place where "more was built" doesn't translate to "more coverage in production," and it's worth stating plainly: the original audit found a narrow-but-real chunk-level guardrail (prompt injection/jailbreak regex) that was itself orphaned from the API. Since then, a substantially broader **Guardrails Platform** (`app/ai/guardrails/`) was built — input (prompt injection, scope, PII), retrieval (context sanitization, Source Trust, citation integrity), generation (faithfulness, schema enforcement, PII leakage), and runtime (budget, loop detection) stages, with real policies and weighted risk scoring. **It has zero callers anywhere in the codebase outside its own tests.** `GenerationService`, `StreamingService`, and the new `chat.py` all bypass it entirely — confirmed via a repo-wide search for `app.ai.guardrails` imports outside the package itself. The original, narrower `context/guardrails/` mini-package (rule-based prompt-injection detection over retrieved chunks) is a *different* component and is still the only guardrail logic that would run at all, and only if `ContextBuilderService` were ever called (which, per §4.1, it isn't).

Net effect: guardrail *capability* is materially better than the original audit found; guardrail *coverage in a live request* is unchanged at effectively zero, because both the narrow original guardrail and the new broad platform depend on call paths (`ContextBuilderService`, `GenerationService`/`StreamingService` guardrail hooks) that don't exist yet.

### 4.7 Validation & Error Handling

**Validation is substantially fixed.** `GenerationService._execute_once()` now calls a real `ValidationService` covering input (empty-prompt, token-budget, provider-limits, context), output (schema, JSON, citation), and hallucination (lexical-overlap groundedness, no LLM judge) stages, producing a weighted `ValidationReport` on every result, and driving an opt-in regeneration loop on output-stage failures. This closes essentially all of the original audit's §4.7 validation gap.

**Error handling is unchanged and still a real gap.** Verified directly this re-audit: `GenerationError` (`runtime/generation/exceptions.py`) and `EmbeddingError` (`knowledge/embeddings/exceptions.py`) both still inherit from plain `Exception`, not `AppException`. Any of these exceptions reaching a route — which is now a live possibility, since `/chat/stream` actually calls `GenerationService` — still falls through to the generic catch-all handler and returns an opaque 500 with no domain-specific status code or error code, even though `register_exception_handlers()` already knows how to map `AppException` subclasses properly. This is a cheap, still-open fix (subclass `AppException` instead of `Exception`) that's more consequential now than in the original audit, since there's finally a live route that can trigger it.

**Resilience is now real for generation, unchanged for everything else.** `_execute_with_retry` (exponential backoff, `config.max_retries`) wraps every provider's `generate()`, a genuine improvement over the original "no retry/backoff library anywhere" finding. There are still no circuit breakers anywhere, and Qdrant/S3 calls still rely on whatever the underlying SDK does natively.

### 4.8 Evaluation & Quality Assurance — completely unchanged

Still the starkest gap in the report, verified unchanged in this re-audit: every file under `app/ai/quality/{benchmarks,evaluation,experiments,regression,telemetry,tracing}/` is a 0-line `__init__.py`. No golden dataset, no LLM-as-judge scoring, no RAGAS/DeepEval-style automated evaluation, no regression gate. `tests/evaluation/*` and `tests/security/*` remain 0-byte scaffolds. None of the intervening work (Routing/Caching/Validation/Streaming/Guardrails) touched this area, which makes sense given each of those shipped with their own unit tests rather than an end-to-end evaluation harness — but it does mean there is still no way to know, e.g., whether the new Routing Platform's model choices actually produce better answers, or whether the Validation Platform's hallucination scores correlate with real hallucinations.

### 4.9 Testing — meaningfully improved, still skewed

The most significant testing change since the original audit: `apps/api/app/ai/runtime/generation/` went from **zero** test files to over 35, spanning providers, catalog, routing (+ scoring), caching (+ exact/policies), validation (+ input/output), and streaming — plus a new `tests/unit/ai/runtime/events/` tree and `tests/integration/ai/test_chat_stream.py` exercising the live SSE endpoint end-to-end. The Knowledge Platform's own coverage is unchanged (real, substantial, unevenly distributed). `documents.py`/`auth.py` route-level coverage and a CI coverage gate remain as originally found — untouched.

### 4.10 Agentic-Flow Readiness — unchanged except for one building block

Tool/function-calling infrastructure is now real at the provider layer: all 5 providers forward `request.tools` to their SDK call. This is a genuine, if currently unused, building block — nothing in the codebase constructs a `ToolDefinition` list and drives a tool-execution loop yet, so it's plumbing without a consumer, the same category `ProviderCapabilities.tool_calling` was in before (just one layer more real). Everything else in this category is unchanged from the original finding: LangGraph still not installed, no agent/planner/orchestrator classes anywhere, no MCP implementation, and — as detailed in the Re-Audit Delta above — conversation memory now exists at the persistence layer but is still flattened into a single-message prompt rather than driving genuine multi-turn provider behavior.

---

## 5. Gap Inventory (Prioritized)

Re-prioritized against current reality. Items resolved since 2026-07-15 have been removed from this list entirely (see §0 for what they were); everything below is either still open or newly surfaced.

### P0 — The one thing that would make this an actual RAG product
1. **Wire retrieval + `ContextBuilderService` into `chat.py`.** This is now the single highest-leverage gap in the entire codebase: the hand-off type (`PromptContext`) exists, the pipeline that builds a real one exists and is well-tested, and the consumer (`StreamingService.stream_generate`) already accepts a `GenerationRequest` carrying it — `chat.py` just needs to call retrieval and `ContextBuilderService` before constructing the request, instead of hardcoding an empty context. Doing this also automatically activates the (currently orphaned) chunk-level guardrail and citation pipeline, since both live inside `ContextBuilderService.build()`.

### P1 — Needed before this is safe/affordable to run for real users
2. **Make AI-domain exceptions inherit `AppException`** instead of plain `Exception` — still open, still cheap, now more consequential since `/chat/stream` is a live path that can actually surface these exceptions to a real caller as an opaque 500.
3. **Fix the production JSON-logging bug** — add the missing `structlog.processors.JSONRenderer()` call in `core/logging.py`'s production branch; verify against the actual deployed config, since log-aggregation correctness depends on it.
4. **Wire the Guardrails Platform (`app/ai/guardrails/`) into `GenerationService`/`StreamingService`.** The platform is built to a real MVP standard and has zero callers — this is the same shape of gap as #1 (a complete subsystem with no consumer), just for safety rather than for RAG quality.
5. **Timeout plumbing for Gemini and Ollama** — the 2 of 5 providers whose SDK client construction still doesn't receive `config.timeout_seconds`.

### P2 — Needed to operate this with confidence at scale
6. **Tracing/APM** — pick one of OpenTelemetry, LangSmith, or Langfuse (the `langsmith_api_key` setting still exists, unused, four platforms later) and instrument the generation call path, now including the new streaming path.
7. **Metrics** — build out Prometheus behind the existing (still unwired) `MetricsRecorder` interface, or replace it; emit latency/cost/token histograms per provider/model, and stream-specific metrics (TTFT, tokens/sec, cancellation rate) the Streaming Platform's own docs already call out as future work.
8. **Evaluation harness** — still the single largest gap in the report by scope: golden Q&A datasets, retrieval-precision and faithfulness/groundedness scoring (test files already scaffolded, still empty), and a regression gate in CI. More urgent now than in the original audit, since there's a Routing Platform making model choices and a Validation Platform scoring hallucinations with nothing measuring whether either is actually working.
9. **Per-user/per-tenant cost aggregation and budget alerting**, now that per-request `estimated_cost_usd` is real and available to aggregate.
10. **CI test-coverage gate**, now that `runtime/generation` coverage is real enough to actually gate on.

### P3 — Roadmap items (agentic flows + RAG-adjacent polish), from scratch or near-scratch
11. **A real multi-message provider API** — `build_messages()` still only ever emits one system + one user message; this is what's actually blocking conversation history from being provider-native instead of transcript-flattened.
12. **LangGraph adoption** — still not installed; needed before any real orchestration (multi-step retrieve→generate→verify, or agentic tool use) is possible on top of the tool-calling plumbing that now exists.
13. **A tool-execution loop** that actually drives the `request.tools` plumbing all 5 providers now support.
14. **MCP** — still zero code, per the roadmap docs' Phase 6 plan.
15. **Streaming rate limiting / per-user concurrent-stream cap** — called out in the Streaming Platform's own "Production Considerations" section as a known gap.
16. **L3 Session Cache wiring** — implemented, still nothing calls it, now that a real `Conversation`/session concept finally exists to key it on.
17. **Native provider prompt-caching** (Anthropic/OpenAI) — distinct from and complementary to this app's own L1/L2/L3.

---

## 6. What's Already Good (worth preserving as-is)

Everything from the original audit's list still holds, plus what's been added since:

- The **composition-root pattern** (`create_*()` factory functions building registries from `settings`) is consistent across every platform added since the original audit too (Routing, Caching, Validation, Streaming, Guardrails) — this discipline held up under real growth, not just in the original core.
- **Pydantic discipline** (`extra="forbid"`, `StrEnum`, frozen configs) is applied consistently in all new code as well.
- **Hybrid retrieval with real RRF fusion + reranking** — unchanged, still more sophisticated than what many production RAG systems ship with initially, and still waiting for a consumer.
- **The embedding cache's fail-open design** is now the confirmed template a second time over: the Runtime Caching Platform's L1/L2/L3 providers all fail open on backend errors too, exactly the right resilience posture, applied consistently rather than reinvented.
- **The Streaming Platform's cache-hit replay design** (synthetic token events on a cache hit, rather than silently returning a non-streamed payload) is a genuinely good, non-obvious correctness fix made during this cycle — it's the kind of detail that's easy to get wrong (breaking the streaming contract on the "fast path") and was caught before shipping.
- **Structured logging conventions** (`structlog.get_logger()`, dot-namespaced events, kwargs-not-f-strings) remain consistent across every new platform — the one real observability convention this codebase has keeps being followed correctly, even as the actual production-JSON bug around it goes unfixed.

---

## 7. Bottom Line

ResearchMind AI closed its single most-cited gap this week — a real HTTP path now reaches a real LLM and streams a real answer back, with real persistence, real cost accounting, real caching, real validation, and real routing behind it. That is not a small thing, and the operational shell it was built on top of (composition roots, provider abstraction, Pydantic discipline) proved itself by absorbing five new platforms cleanly in a few days without architectural strain.

But the harder problem the original audit identified — **two well-built subsystems that don't talk to each other in production** — is not solved, it's just relocated. It used to be "generation is unreachable at all." It is now "generation is reachable, but only with an empty context, so retrieval, reranking, citations, and guardrails — the actual RAG pipeline this platform exists to run — still never execute for a real user." Closing that one gap (§5, P0 #1) is now the highest-leverage single change available: it activates three dormant subsystems at once (retrieval, `ContextBuilderService`'s guardrails, and citations) for the cost of one wiring change, using types and services that already exist and are already tested. Everything else on this list — tracing, evaluation, the `AppException` gap, the logging bug, the unwired Guardrails Platform — matters, but none of it changes whether a user gets a cited, grounded answer instead of a raw LLM guess, which is still the one thing this platform doesn't yet do end-to-end.
