# Resolved: USER memory (durable preferences) is captured and applied

**Status:** ✅ Read side wired, 2026-08-12 (`PRIORITIZED_ROADMAP.md` Wave 2,
"User-profile memory read-side wiring"). See "Resolution" section at the
bottom for what shipped and what deliberately stayed open.
**Source:** Conversation, 2026-07-26 — clarifying how ResearchMind keeps a
user profile/preferences over time, as an expansion of Session and Semantic
memory. Verified by direct read of `app/ai/memory/`, not from memory of the
PRD.

## The four-tier memory model

| Tier | Backend | Scope | Lifecycle |
|---|---|---|---|
| **SESSION** | Valkey | one conversation | 7-day TTL, auto-expires (`memory_session_ttl_seconds`) |
| **SEMANTIC** | Postgres + Qdrant | cross-session topics/facts | durable, embedded, searchable |
| **USER** (`app/ai/memory/profile/service.py`) | **Postgres only, no vector index** | durable preferences — "favorite models, writing style, response preferences, preferred providers, research interests" per its own docstring (PRD §9.3) | durable, looked up by owner, not searched semantically |
| **RESEARCH** | Postgres + Qdrant | prior research topics/findings | durable, embedded |

USER memory is a real, deliberate expansion beyond Session/Semantic — same
`MemoryRecord` shape, same `MemoryService` orchestrator, but Postgres-only
(no embedding) since preferences are meant to be fetched by owner ID, not
fuzzy-matched by meaning.

## What's built (the write side — solid)

- **Two extraction paths**, both running post-turn via
  `MemoryExtractionOrchestrator` (`app/ai/memory/extraction/orchestrator.py`):
  1. **Explicit trigger phrases** ("remember this," "from now on," "always
     use," "please avoid," etc., `policy/service.py`'s `_EXPLICIT`/`_DURABLE`
     tuples) → extracted synchronously, immediately.
  2. **Repeated-interest promotion** (`policy/interest_promotion.py`) — a
     cheap, privacy-scoped Redis counter (topic text is hashed, never stored
     in plain Redis keys) tracks distinct *sessions* mentioning the same
     lexical topic. Only after a topic appears in **2 distinct sessions**
     (`memory_interest_promotion_min_distinct_sessions`) within a 90-day
     window (`memory_interest_promotion_ttl_seconds`) does it become
     eligible for **one bounded LLM validation call** deciding whether to
     actually promote it to a durable USER (or RESEARCH) memory. Cheap
     lexical filter first, LLM only for survivors — avoids paying for
     validation on every message.
- Both paths converge on `MemoryService.remember_extracted()`, which dedupes:
  an exact-content match updates the existing row's provenance/importance
  instead of creating a duplicate row.
- Generic CRUD is exposed via `/memory` (not preference-specific endpoints):
  `POST /memory` (remember, `type=USER`), `GET /memory/context`,
  `GET /memory/{id}`, `PUT /memory/{id}`, `DELETE /memory/{id}`.
  `UserMemoryService.list_preferences()` backs a recency listing (no
  ranking — USER has no embedding index to rank against).
- Retention: no hot/warm/cold decay exists. A dedicated recurring worker calls
  `MemoryLifecycleService.sweep_stale()` with configurable per-type age and
  importance policies, a Valkey singleton lock, bounded batches, metrics, and
  row-level failure isolation. It defaults to dry-run; production deletion is
  an explicit rollout decision.

## Historical gap — resolved 2026-08-12

> The diagnosis below records the pre-resolution implementation and is kept as
> decision history. It does not describe the current runtime behavior; see
> “Resolution” below.

**`MemoryContext` (the bundle injected into every live Chat/Research turn)
deliberately excludes `user_memories`.** `app/ai/memory/models.py:63-67`'s own
comment: *"preferences apply globally rather than needing to be assembled
per-turn."* And `format_memory_context()`
(`app/ai/memory/services/formatting.py`) — the function that actually turns
a `MemoryContext` into prompt text prepended before generation — only ever
renders `session_memories`/`semantic_memories`/`research_memories`. USER
memory never appears in a rendered prompt, full stop.

Grepped for any consumer of the specific fields USER memory's own docstring
names as its purpose (favorite model, writing style, preferred provider) —
**zero hits anywhere outside the memory package itself.** `RoutingService`'s
model/provider selection doesn't read it. No formatting/style step reads it.

**Net effect:** a preference can be captured, deduplicated, stored durably,
and read back via the `/memory` API — but it currently has no live
consumer. It's a built, tested, wired-for-*writing* subsystem sitting on top
of an unbuilt read side. This is a "not yet wired" gap, not a design mistake
— the exclusion from `MemoryContext` looks like a deliberate PRD choice
(preferences are global config, not a per-turn retrieval concern), but
nothing then built the global-config read path that choice implies.

## Don't confuse this with ROADMAP Phase 1.6

`ROADMAP.md:101` separately lists **"User Profile (preferences, AI
settings) — ⏳ Planned, not started."** That's a different thing: an
explicit settings UI where a user directly sets preferences. This document
is about the USER *memory* type, which is inferred from conversation
behavior via the extraction pipeline above. Neither currently feeds back
into generation — Phase 1.6 because it hasn't been built at all, this one
because the read side isn't wired despite the write side working.

## Historical open questions before implementing the fix

1. **Where does USER memory get read?** Two candidate injection points,
   not mutually exclusive:
   - **Prompt content** — extend `format_memory_context()`/`MemoryContext`
     to include a `user_memories` section, formatted once per session
     (not per-turn re-fetched) given the "applies globally" framing.
   - **Routing/behavior** — `RoutingService` reads a preferred-provider/
     favorite-model USER memory before falling to its own scoring, and/or
     a writing-style preference gets folded into the system prompt
     template rather than the retrieved-context block.
2. **Cost/latency**: reading USER memory needs to happen somewhere in the
   hot path for every turn (unless cached) — is a per-request Postgres
   lookup of a handful of rows cheap enough to just always do, unlike the
   semantic/research durable-retrieval path's `DurableMemoryAvailabilityService`
   short-circuit (built specifically because *that* lookup is comparatively
   expensive)?
3. **Conflict resolution**: if a USER memory says "always use Claude" but a
   request also carries an explicit `routing_strategy` override, which
   wins? Needs an explicit precedence decision, not an implicit one.
4. **Staleness**: preferences can contradict each other over time ("I
   prefer concise answers" then later "give me detailed answers") — the
   current dedup is exact-content-match only, so two contradictory
   preferences would both persist as separate rows with no supersession
   logic. Worth deciding before this becomes user-visible.
5. **Should this wait for Phase 1.6 (explicit settings UI)?** An explicit
   settings page might be the simpler, less ambiguous product surface for
   many of the same preferences (favorite model, writing style) — inferred
   USER memory may be better scoped to softer signals (research interests)
   that a settings form wouldn't naturally capture. Worth deciding which
   preferences belong to which mechanism before wiring either one's read
   side.

## Resolution (2026-08-12)

Prompt-content injection path (open question 1's first option) is now wired,
end to end, with zero call-site changes needed in any consuming runtime:

- `MemoryContext` (`app/ai/memory/models.py`) gained a `user_memories` field.
- `MemoryService.get_context()` now fetches
  `self._user.list_preferences(owner_id=owner_id, limit=top_k)` unconditionally
  alongside the existing session fetch — an uncached Postgres query every
  turn, same as session's Valkey fetch, deliberately not wrapped in the
  semantic/research try/except-and-continue pattern (answers open question 2:
  a handful-of-rows owner-scoped lookup is cheap enough to just always do; no
  new caching layer was added).
- `format_memory_context()` renders a new "Durable user preferences (apply to
  every turn):" section, positioned right after session state.
- Because Chat, Linear Research, Deep Research proposal, and Deep Research
  execution all call the shared `format_memory_context()`/`with_memory_context()`
  helpers rather than touching `MemoryContext` fields directly, all four
  surfaces now surface USER memory with no per-runtime code change.

**Same-day follow-up (2026-08-12): precedence + write-path.**
- **Conflict resolution (open question 3, partially answered):** the current
  turn's explicit instruction now always wins over a stored USER preference
  when they conflict — `format_memory_context()`'s closing text states this
  directly ("If anything above conflicts with an explicit instruction in the
  user's current question, the current question always wins"), and the USER
  section heading was softened from "apply to every turn" to "defaults, see
  precedence note below" to match. This is prompt-text guidance only, not
  code-enforced.
- **Preference feedback → `USER` memory write path** (a separate Wave 2
  roadmap line item, done together with the above): `FeedbackService.submit()`
  now writes a USER memory from a feedback comment, but only when E11's
  existing objective/preference classifier (`CommentClassificationService`,
  see `comment-classification-platform` memory) judges it `PREFERENCE` —
  `OBJECTIVE` comments (factual answer-quality complaints, e.g. "cited the
  wrong paper") are never written, since they describe the answer, not the
  user. Reuses `MemoryService.remember_extracted()` (the same convergence
  point the explicit-trigger and interest-promotion write paths already use)
  and `score_importance()` for the importance score — no new classifier or
  scoring logic was built. Best-effort: a memory-write failure never fails
  feedback submission.

**Second same-day follow-up (2026-08-12): staleness/supersession, closing
open question 4.** `MemoryService.remember_extracted()`'s dedup was
exact-content-match only, so two USER preferences that mean the same thing
in different words -- or that flatly contradict each other ("prefers
concise answers" then later "prefers detailed answers") -- both persisted
as separate rows forever, with no supersession. Fixed with a second tier,
USER-type only, that runs when the exact-match check misses: a new
`PreferenceSupersessionService` (`app/ai/memory/policy/supersession.py`,
same cheap-bounded-LLM-call pattern as `CommentClassificationService`/
`WebSearchNecessityService`/`MemoryExtractionService`, Groq-primary/
OpenAI-fallback via the existing `_cheap_memory_providers()` composition)
compares the new statement against the owner's existing USER preferences
(via `UserMemoryService.list_preferences()`) and asks which one, if any,
it replaces. A match updates that row in place (`UserMemoryService.update()`)
instead of creating a second row -- the "latest version wins" resolution,
not a soft-delete/superseded-flag scheme, so no new column or read-path
filtering was needed. Fails closed to "no supersession" (create a new row)
on any classification failure, out-of-range index, or when
`settings.memory_preference_supersession_enabled` is off (default on).
Scoped to `remember_extracted()`'s three inferred write paths (explicit
trigger, interest promotion, feedback) only -- the direct `POST /memory`
API and `research/service.py`'s raw-turn SESSION write are untouched,
since an explicit, deliberate API call to create a memory should create
one, not silently overwrite another.

**Bug found and fixed while verifying owner-scoping (2026-08-12):**
`GET /memory/context` (`app/api/v1/memory.py`, `MemoryContextResponse` in
`app/schemas/memory.py`) was never updated when `user_memories` was added to
`MemoryContext` — the prompt-injection path (Chat/Research) picked it up for
free via the shared `format_memory_context()` helper, but this direct API
view of the assembled context silently kept omitting USER preferences from
its JSON response. Fixed: `MemoryContextResponse` gained a `user_memories`
field, the route now populates it. Covered by
`tests/api/test_memory.py` (new file — no test existed for this route at
all before).

**Deliberately declined, by explicit user instruction (2026-08-12):**
- **Routing/behavior injection** (open question 1's second option) — user
  decided not to make `RoutingService` memory-aware ("no need memory to
  routing strategy"). Not just deferred pending a decision; this option is
  closed unless revisited later by explicit request.
- **Settings-UI overlap** (open question 5) — not resolved; this pass treats
  all captured USER memory content as safe to surface as prompt text
  regardless of which preferences might eventually move to an explicit
  settings page.
