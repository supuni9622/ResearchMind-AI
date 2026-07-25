# ADR-037 — Research Intelligence MCP Paper Search Platform

**Status:** Accepted
**Date:** 2026-07-25
**Related ADRs:** ADR-036 (Web Search Tool Platform and the Web-Search-Approval
Checkpoint), ADR-034 (Deep Research Product Routing)
**Related PRDs:** `prds/3. mcp_server_setup.md` (server connection guide, the
scope actually built here), `prds/1.researchmind_mcp_integration_prd.md`
(a larger production-hardening spec -- explicitly deferred, see Consequences)

---

## Context

ResearchMind needed to become an MCP **client** of an external "Research
Intelligence MCP" server exposing `search_papers` (and 6 other tools) over
`streamable-http`. The product requirement was narrow and concrete: let Chat
optionally search papers relevant to a turn, let Deep Research optionally
suggest related papers once a report finishes, and leave Linear Research
untouched. No MCP client code existed anywhere in the repo before this.

A second PRD (`prds/1...`) already in the repository describes a
substantially larger production integration: a cached, lock-guarded JWT
service-token provider (Cognito/issuer-backed), retry-with-backoff, a
9-category error taxonomy, `X-Request-ID`/`X-Correlation-ID` propagation,
and typed methods for all 6 MCP tools. Confirmed with the user that this
pass targets the leaner scope only -- matching what was actually asked for
and PRD #3's local/dev `streamable-http` path (no auth required, or a static
bearer token) -- and treats the fuller PRD as a later hardening pass, not
a mistake to reconcile now.

## Decision

### Platform-owned, framework-independent paper search -- mirrors the Web Search Tool Platform exactly

`apps/api/app/ai/tools/paper_search/` is a small, standalone platform
(canonical `PaperSearchRequest`/`PaperSearchResult` models, a
`PaperSearchProviderInterface`, a `PaperSearchService` that applies
policy/caching and normalizes results, a provider registry). It has no
LangGraph or Chat-runtime imports -- both runtimes depend on it, matching
every other platform boundary in this codebase (Web Search, Generation,
Guardrails, Retrieval). The file layout, composition-root (`create.py`,
registers a provider only if configured), and "`.available` degrades to
`False` rather than raising" convention are copied 1:1 from
`app.ai.tools.web_search`.

### Single tool, single provider, no retry loop

Only `search_papers` is wired (`ResearchIntelligenceMCPProvider` in
`providers/mcp_client.py`, using the official `mcp` SDK's
`streamablehttp_client` + `ClientSession`, a fresh connection per call). The
other 6 tools (`get_paper`, `get_paper_citations`, etc.) are out of scope --
neither Chat's per-turn search nor Deep Research's end-of-run suggestion
needs them. Auth is an optional static bearer token
(`settings.mcp_papers_auth_token`), not a cached/refreshed service-token
provider; failures are not retried, matching this codebase's existing
best-effort convention for optional collaborators (memory, title generation,
web search) -- callers already degrade gracefully on any exception, so a
retry loop would add complexity without changing the failure mode a caller
sees.

### Caching: mirrors the query-embedding cache, not the Generation Runtime Caching Platform

`apps/api/app/ai/tools/paper_search/cache/` is a Valkey-backed,
fail-open, TTL cache (`ValkeyPaperSearchCache`), keyed by
`sha256(query|max_results)`. This mirrors
`app.ai.knowledge.cache.query_embeddings` (a simple "cache one external
call's result behind get/set" shape) rather than the generation-specific
L1/L2/L3 Runtime Caching Platform (`app.ai.runtime.generation.caching`),
which is tightly coupled to `GenerationRequest`/`GenerationResult` and the
wrong fit for caching a tool call's JSON result.

### Chat: toggle-gated, no necessity decision, no approval

`ChatStreamRequest.paper_search_enabled: bool = False` mirrors
`web_search_enabled` exactly -- toggling on is the approval, once, per turn
(Chat has no interrupt/resume mechanism to pause on). Unlike Web Search's
Chat integration, there is deliberately **no** necessity-decision LLM call
first: `run_chat_paper_search()` (`app/ai/runtime/chat/paper_search.py`)
always searches when enabled, using `user_prompt` directly as the query.
Confirmed with the user -- cheaper and simpler than mirroring AUTO mode's
necessity gate, and avoids introducing a second necessity-service surface
with the same fragile-structured-output failure mode ADR-036 already hit
once with `gpt-5-nano`.

### Deep Research: a non-blocking event, not a fourth approval checkpoint

`ResearchProposalRequest.paper_suggestions_enabled: bool = False` (opt-in,
Deep-Research-only, mirrors `web_search_mode`'s scoping -- never added to
the base `ResearchRequest` Linear Research uses). Unlike the web-search
approval checkpoint (ADR-036), this is **not** a `interrupt()` node: a new
`suggest_related_papers` node is inserted sequentially between
`persist_final_report` and `END`, wrapped in one broad `try/except` that
never re-raises and an explicit `asyncio.wait_for` timeout guard on top of
the provider's own timeout. The report is already durably persisted by the
time this node runs, so there is nothing to gate -- the user's explicit ask
was "additional feature, should not break the flow," and a report that's
already been written must never be held hostage by a slow or broken MCP
server. On success it emits `RESEARCH_RELATED_PAPERS_COMPLETED` carrying the
suggested papers directly in the event's metadata (title/authors/year/url,
capped at 5); on anything else (disabled, unconfigured, empty, or any
exception) it emits `RESEARCH_RELATED_PAPERS_SKIPPED` and the run reaches
`END` exactly as it would have without this feature.

### `LangGraphResearchEventAdapter.progress()` gains an opt-in `extra_metadata` param

Every other Research Runtime event carries only a stable `{"label": ...}`
payload by design ("internal node names, task questions, evidence excerpts
... never cross this boundary" -- ADR-032/ADR-036). Surfacing the actual
suggested-paper list requires breaking that rule for exactly one event type.
Rather than loosen the rule generally, `progress()` and
`ResearchRuntimeEventJournal.publish()` both gained an optional
`extra_metadata: Mapping[str, object] | None = None` parameter, merged into
`StreamEvent.metadata` alongside `label`. Default `None` leaves every one of
the ~15 existing call sites across `execution.py`/`run_service.py`
byte-for-byte unaffected; only `suggest_related_papers` passes a value.

### Frontend needs almost no new plumbing for the event log itself

`use-deep-research.ts`'s SSE handler already generically logs
`{type, label, timestamp}` for any event the backend emits (`label` resolved
from `event.metadata?.label`), so the three new event types
(`research_related_papers_started/completed/skipped`) render in the
existing `EventLog` component automatically, without a single frontend
code change. Only the actual paper list needed new plumbing: one more `if`
branch reading `event.metadata?.papers` off the `COMPLETED` event, a new
`DeepResearchTurn.relatedPapers` field, and a small read-only card rendered
after the report completes (no approve/reject controls, since there is no
checkpoint to decide on).

## Consequences

- Enabling paper search requires both a global switch
  (`MCP_PAPERS_ENABLED`) and `MCP_PAPERS_SERVER_URL`; either being absent
  degrades `PaperSearchService.available` to `False` -- Chat's toggle and
  Deep Research's opt-in field both silently no-op rather than erroring.
- `prds/1.researchmind_mcp_integration_prd.md`'s full scope -- JWT
  service-token provider with cached/locked refresh, retry-with-backoff,
  9-category error taxonomy, correlation-ID propagation, and typed methods
  for the remaining 5 tools -- is explicitly deferred, not built. Revisit if
  this integration needs to run against a production ECS deployment behind
  real service-to-service auth, or if `get_paper`/`get_related_papers`
  become needed by a future feature.
- The MCP server's `search_papers` structured-output schema has no published
  contract in this repo; `providers/mcp_client.py` parses it leniently
  (tries `papers`/`results`/`items` list keys) rather than pinning to one
  exact shape -- revisit once a real schema is available.
- A fresh MCP session (streamable-http connect + `initialize()`) is opened
  per call rather than held persistently -- acceptable given both call
  sites fire at most once per Chat turn / Deep Research run, and the cache
  absorbs repeats; revisit if call volume or the MCP server's connection
  overhead ever makes this a bottleneck.
