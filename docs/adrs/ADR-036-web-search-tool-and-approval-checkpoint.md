# ADR-036 — Web Search Tool Platform and the Web-Search-Approval Checkpoint

**Status:** Accepted
**Date:** 2026-07-25
**Related ADRs:** ADR-034 (Deep Research Product Routing), ADR-032 (LangGraph Checkpointing and
Event Adaptation)
**Related PRD:** `prds/2. web_search_tool_platform_prd.md`

---

## Context

The Research Runtime (ADR-034) grounds every report in uploaded documents and
persisted research/memory context. It has no way to reach current or
external information. `web_search_tool_platform_prd.md` specifies a full
production Web Search Tool Platform (search + a separate SSRF-hardened Web
Fetch Platform, source-trust scoring, a dedicated evaluation/benchmark
harness, multi-provider fallback). That is a substantially larger scope than
this milestone needs.

The concrete product requirement driving this work is narrower: the Deep
Research agent should be able to decide, mid-run, that it needs the public
web, but it must ask for human approval before actually searching unless the
user pre-authorized it; a rejection must fall back to exactly today's
behavior; and none of Chat, Linear Research, or Deep Research may change
behavior for a deployment that hasn't opted in.

## Decision

### Platform-owned, framework-independent search

`apps/api/app/ai/tools/web_search/` is a small, standalone platform
(canonical `WebSearchRequest`/`WebSearchResult` models, a
`WebSearchProviderInterface`, a `WebSearchService` that applies policy/budget
and normalizes results, a provider registry). It has no LangGraph or
Research Runtime imports — the Research Runtime depends on it, not the other
way around, matching every other platform boundary in this codebase
(Generation, Guardrails, Retrieval).

### Tavily only, content-only (no separate Web Fetch Platform yet)

`TavilyWebSearchProvider` calls Tavily's REST API directly via `httpx` (no
new SDK dependency, matching this codebase's existing direct-`httpx`
convention). Tavily's search API extracts page content server-side, so
ResearchMind itself never issues an outbound request to an arbitrary,
attacker-influenced URL — there is no new SSRF surface to defend. The PRD's
separate SSRF-hardened Web Fetch Platform (§14) is therefore deliberately
**not** built in this pass; it becomes necessary only if a future provider
requires ResearchMind to fetch raw URLs itself. Fetched/extracted text is
still scanned through the **existing** Context Guardrails Platform
(`ContextGuardrailService` / `RuleBasedGuardrailProvider`, whose pattern
table already includes tool-call/execute-code/browse triggers) before it
becomes evidence — prompt-injection defense is reused, not rebuilt.

### The decision reuses the existing gap-research loop, not a new node family

The Deep Research graph (`multi_wave_research.py`) already has a bounded
"the agent doesn't have enough evidence" loop: `review` can return
`RESEARCH_GAPS` with one targeted question, which routes to
`prepare_gap_research` → `retrieve_gap_task` → `aggregate_gap_evidence` →
back to `synthesize`, bounded by `ResearchPlanningPolicy.max_review_iterations`
and a cost ceiling. Three new nodes (`evaluate_web_search_need`,
`await_web_search_approval`, `search_web_gap`) are inserted as an alternative
branch inside this same loop rather than as a parallel graph, so the feature
inherits the existing iteration/cost/recursion budget for free and a decline
falls back to the exact pre-existing `prepare_gap_research` node — "reject
and the run continues exactly as it would have without this feature" is true
by construction, not by a separate compatibility path.
`REQUIRED` mode additionally forces one round from `route_after_review`'s
`PASS` branch (guarded by a `web_search_count == 0` check) so "at least one
web source" holds even when the reviewer never flags a gap.

### A third interrupt checkpoint, mirroring the plan-approval checkpoint exactly

`await_web_search_approval` follows the `await_plan_approval`
(`interrupt()`, no side effects before the call since LangGraph replays the
node body on every resume, a conditional edge routes on the resumed
decision) pattern precisely, including a new `ResearchRunStatus.
AWAITING_WEB_SEARCH_APPROVAL`, lifecycle transitions, `ResearchRunService.
record_web_search_decision`, and an `execution.py` resume branch. Unlike
plan/report rejection, a malformed resume payload is treated as a rejection
rather than raised — there is always a safe fallback here (the document-only
gap path), so failing closed on the *search*, not the whole run, is the
correct default (PRD §5.7, §38 rule 13: "fail open for optional search
branches").

**`REQUIRED` mode never pauses for approval.** The user already explicitly
required web search; asking again would be redundant. Only `AUTO`'s own
judgment call prompts, and only when `web_search_auto_approve` (the
pre-authorize toggle) is `false`.

### Evidence flows through the existing evidence model, unchanged in shape

`ResearchEvidenceReference`/`ResearchTaskResult`/`ResearchEvidenceBundle`
already use plain `str` identifiers, not FK'd UUIDs, and synthesis validates
citation IDs only against the run's own `evidence.citation_ids` set — not
against the document-bound `Citation` platform model (which requires a real
`document_id: UUID` and would break if forced to represent a URL). Web
results populate the same reference shape (`document_id` = normalized URL,
`citation_id` = `"web:{id}"`) plus one new optional field,
`source_type: Literal["document", "web"] = "document"`, for provenance —
no changes to the Citation platform, PDF renderer, or synthesis/review
prompts, and old checkpointed state still validates (the field defaults).

### A dedicated cheap model pair for the necessity decision, separate from the app's main models

"Does this need the web" is answered by a small structured-output call using
a registry built specifically for this decision
(`app.ai.runtime.research.web_search.create`), pinned to `gpt-5-nano`
(OpenAI) or `claude-haiku-4-5` (Claude, a new catalog entry — no cheap Claude
tier existed before this). This is deliberately **not** the same mechanism
as `RoutingStrategy`/explicit-provider selection against the shared
`GenerationRegistry`: that registry has one model per provider used for
*every* call (synthesis included), so forcing a provider there would still
use whatever model synthesis uses, not a cheap tier. A second, minimal
`GenerationService`/`GenerationRuntime` pair, registered only if the
corresponding API key is configured, isolates this one bounded call's model
choice from the rest of the app's configuration. If neither OpenAI nor
Claude is configured, the decision falls through once more to the shared
production runtime via `RoutingStrategy.CLASSIFICATION` (not `AUTO`, which
hard-defaults to Groq) — the feature is never unavailable, only
de-prioritized to whatever's actually configured.

### API surface is additive and scoped to Deep Research only

`web_search_mode` (`disabled`/`auto`/`required`), `web_search_auto_approve`,
`include_domains`/`exclude_domains` are added to `ResearchProposalRequest`
only — not the base `ResearchRequest` used by Linear Research's `/research`
and `/research/stream`. Chat has no dependency on the Research Runtime at
all. Both therefore require zero code changes and their request/response
contracts are byte-for-byte unchanged.

## Consequences

- Enabling web search requires both a global switch (`WEB_SEARCH_ENABLED`)
  and a `TAVILY_API_KEY`; either being absent degrades `WebSearchService.
  available` to `False` — a run never crashes because search is
  unconfigured, it just behaves as if `web_search_mode` were `disabled`.
- The standalone SSRF-hardened Web Fetch Platform, multi-provider fallback
  (Exa/Brave/MCP), org-wide domain policy management, and the full
  evaluation/benchmark harness from the PRD are explicitly deferred, not
  built. Revisit if a future provider needs ResearchMind to fetch arbitrary
  URLs itself, or if AUTO's necessity-decision quality needs benchmarking
  against a labeled dataset.
- The `AWAITING_WEB_SEARCH_APPROVAL` TTL-expiry sweep, dispatch-reopen
  atomicity, and interrupt-kind detection all had to be extended in lockstep
  with the plan-approval checkpoint's existing plumbing — any *future*
  fourth checkpoint should budget for the same five-file surface
  (`types.py`, `lifecycle.py`, `run_service.py`, `execution.py`, a new
  `*_inspection.py`) this one required.
