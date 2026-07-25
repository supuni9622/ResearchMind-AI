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

### An earlier entry point: catching topical irrelevance before synthesis, not just after (2026-07-25, same day, later)

The post-review loop above only fires *after* a full synthesis pass, and
only if the reviewer's deterministic/model checks happen to flag a gap.
They don't: a private corpus that is confidently, fluently, but *entirely*
off-topic for the goal (e.g. asking about climate change against a
knowledge base containing only a mental-health PDF) can still produce
well-formed citations and pass review cleanly — the reviewer checks
citation integrity and coverage, not whether the cited material is
actually about the right subject. The user-visible failure mode was a
synthesized report on the wrong topic, with the mismatch only disclosed in
prose inside the abstract, discovered by the user after the run completed.

The first fix considered was a numeric relevance-score threshold on
`ResearchEvidenceReference.score` at aggregation time. That score is a
Reciprocal Rank Fusion sum (`Σ 1/(60+rank)` across up to three retrieval
lists — dense, sparse, metadata; see
`app/ai/knowledge/retrieval/fusion/rrf.py`), which is rank-derived, not a
semantic-similarity measure, and is bounded to roughly `[0, 3/61]`
regardless of topical relevance — a confidently-wrong top-1 hit in a
single-document corpus scores identically to a genuinely relevant top-1 hit
in a rich one. A raw threshold on it cannot distinguish the two. (A genuine
0-1 relevance signal already exists in the pipeline — the Voyage `rerank-2`
reranker score — but it is computed only to reorder/select the top-k
chunks and then discarded; it never reaches `ResearchEvidenceReference`.
Propagating it would be a larger, higher-blast-radius change to the core
Retrieval Platform models shared by Chat and Linear Research, deferred.)

Instead, `route_after_aggregate` routes to `evaluate_web_search_need`
*unconditionally* whenever web search is `auto`/`required` and available —
right after `aggregate`, before `await_plan_approval` — reusing the same
cheap necessity-decision model, whose prompt now explicitly asks it to
judge topical relevance (not just recency/coverage) from the evidence
excerpts against the goal. This is a judgment call an LLM handles far more
reliably than any single scalar threshold. `REQUIRED` mode's "at least one
web source" guarantee also moved here (deterministic, no LLM call) —
strictly earlier and cheaper than the old post-review-PASS forced check it
replaced, since it now happens before a synthesis call is ever spent.

Because `evaluate_web_search_need`/`await_web_search_approval`/
`search_web_gap`/`aggregate_gap_evidence` are now reachable from two
different points in the graph (this new early entry, and the pre-existing
post-review repair loop), their "what happens when there's nothing to
suggest, or it's rejected" fallback and "where does newly-aggregated
evidence go next" edge both became context-dependent. Both are resolved by
checking `state["plan_decision"]` (`_before_plan_approval` in the code):
unset means this is the early path (fall back to / continue on to
`await_plan_approval`); set means it's the post-review path (fall back to
/ continue on to `prepare_gap_research` / `synthesize`, exactly as before
this change). No new state field was needed — `plan_decision` already
uniquely identifies which side of the (single, once-only) plan-approval
checkpoint the run is on.

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

## Addendum (2026-07-25, same day, latest) — Chat gets web search too, toggle-gated, no approval

The three-flow scope in Context above named Deep Research as the only place
this ADR's approval checkpoint applies, and left Chat and Linear Research
untouched. The user separately asked for Chat to get web search as well
(explicitly excluding Linear Research: "lieart research, don't need it").
Chat has no LangGraph, no interrupt/resume mechanism, and no product reason
to pause a fast conversational turn on an approval click — so this is not
a fourth checkpoint. It reuses the same platform and necessity-decision
service this ADR already built, with the approval question answered once,
up front, by the toggle itself, mirroring `web_search_auto_approve=True`'s
semantics without needing Deep Research's mode enum (Chat has no
REQUIRED/DISABLED distinction, just on/off).

New, Chat-scoped files: `apps/api/app/ai/runtime/chat/web_search.py`
(`run_chat_web_search()` — best-effort, any failure degrades to "no web
search for this turn" rather than failing the turn, matching how every
other optional Chat collaborator — memory, title generation, artifacts —
already behaves) and `apps/api/app/ai/runtime/events/chat/models.py`
(`ChatEventType`: `chat_web_search_started/completed/skipped`, emitted with
`category=EventCategory.TOOL` since Chat's stream had no prior use for that
category). `ChatStreamRequest.web_search_enabled: bool = False` is the new
toggle (schemas/chat.py); both `stream_chat` (SSE) and `stream_chat_ws`
(WebSocket) routes call `run_chat_web_search()` before generation and
prepend its context to the prompt when it found anything, via a small
`_chain_events()` wrapper generator that yields the search's status events
ahead of the underlying token stream. Reuses `WebSearchService`,
`WebSearchNecessityService`, and `normalize_web_search_result` unchanged —
no new provider, model, or evidence-normalization logic. Default off, so
existing Chat behavior is unaffected until a user opts in per-turn.

## Addendum (2026-07-25, same day, later still) — AUTO mode's necessity model swapped from gpt-5-nano to gpt-5-mini

`REQUIRED` mode never calls a model at all (`WebSearchNecessityService.
decide()` short-circuits deterministically for it), so it working in earlier
testing proved nothing about whether `AUTO`'s actual model call worked --
and it didn't: confirmed in production logs that `gpt-5-nano` (the cheapest
tier, this section's original choice) unreliably follows the
structured-output (`json_schema`) contract for this specific call. Its
response wasn't truncated (the existing regeneration `max_tokens`
auto-escalation logic never triggered -- `finish_reason` wasn't a
truncation reason), it just wasn't valid or repairable JSON, both on the
first attempt and the one regeneration retry, so `decide()` correctly
failed closed to "no search needed" -- every single time, silently, since
the necessity-unavailable log only recorded `error_type`, not the message,
until this same pass also added `error=str(exc)` to that log line.

Fixed by switching `web_search_decision_openai_model`'s default from
`gpt-5-nano` to `gpt-5-mini` -- this app's already-proven-reliable default
OpenAI model everywhere else, and still a materially cheaper tier than
main synthesis/review. Paired with two cheap defensive hardenings
regardless of model choice: the system prompt now explicitly demands
JSON-only output (no prose/fences), and `max_tokens`/
`max_regeneration_attempts` were both raised (300→600, 1→2) to give more
headroom before giving up. `web_search_decision_openai_model` remains a
setting an operator can still override back to `gpt-5-nano` if they accept
the reliability trade-off for the marginal extra cost savings.

## Addendum (2026-07-25, same day, later) — two fixes from a real failing run

A live run against a corpus mismatched to the query (asking about climate
change with only a mental-health PDF uploaded) surfaced two more issues:

1. **The early detour was charged against the wrong budget.** `search_web_gap`
   unconditionally incremented `gap_research_count` — the same counter
   `route_after_review` checks against `ResearchPlanningPolicy.
   max_review_iterations` (as low as 1, for `MODERATE` complexity) to bound
   *post-synthesis* repair rounds. Since the early, pre-plan-approval
   detour (this ADR's main addendum above) always runs before any
   synthesis attempt, charging it against that same budget could leave
   zero rounds available for a legitimate post-synthesis citation fix.
   Fixed: `search_web_gap` only increments `gap_research_count` when
   `_before_plan_approval(state)` is false (the post-review context).
2. **A budget-exhausted citation-integrity fix crashed the run outright.**
   Independent of (1) and pre-existing: when `review` returns
   `REVISE_SYNTHESIS` (e.g. the draft used zero citations despite evidence
   existing) but the shared repair budget is already spent — trivial to
   reach with a 1-round `MODERATE` budget once even a single gap-repair
   round has run — `route_after_review` routed to `fail()`, raising an
   unhandled `RuntimeError` and failing the entire run. Per explicit user
   decision, this now routes to `finalize_gap_limitations` instead (the
   same node a budget-exhausted `RESEARCH_GAPS` follow-up already uses),
   publishing the existing draft as `completed_with_limitations` with a
   disclosed citation-integrity limitation, rather than crashing. This
   applies uniformly to both `REVISE_SYNTHESIS` triggers (zero citations
   used, and unsupported/hallucinated citation IDs) — the latter is a
   deliberately accepted trade-off (disclosure over hard failure); revisit
   if hallucinated citations specifically should still fail hard.

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
- `AUTO` mode now always spends one cheap necessity-decision call per run
  (right after aggregation), not only when a post-review gap is found —
  an intentional, small, fixed cost in exchange for catching topical
  mismatch before a synthesis call is wasted on it. `DISABLED` mode and
  runs without web search configured are entirely unaffected (the detour
  is skipped, not just fast-pathed).
- The discarded Voyage `rerank-2` score remains the more principled
  long-term signal for evidence relevance generally (not just this
  checkpoint) if it's ever propagated through `RetrievedChunk`/
  `ContextChunk`/`ResearchEvidenceReference` — noted here as a known,
  deliberately deferred improvement, not a gap introduced by this change.
- The `AWAITING_WEB_SEARCH_APPROVAL` TTL-expiry sweep, dispatch-reopen
  atomicity, and interrupt-kind detection all had to be extended in lockstep
  with the plan-approval checkpoint's existing plumbing — any *future*
  fourth checkpoint should budget for the same five-file surface
  (`types.py`, `lifecycle.py`, `run_service.py`, `execution.py`, a new
  `*_inspection.py`) this one required.
