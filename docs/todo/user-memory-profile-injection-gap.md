# TODO: USER memory (durable preferences) is captured but never applied

**Status:** Not started — investigation/clarification only, verified against
code on 2026-07-26. No implementation decision made yet.
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
- Retention: no automatic hot/warm/cold decay yet. `MemoryLifecycleService.
  sweep_stale()` (`lifecycle/service.py`) removes low-importance
  (`importance_score < 0.3`) USER/SEMANTIC/RESEARCH rows untouched for 90+
  days — but it's deliberately callable-but-unscheduled; nothing in this
  codebase runs recurring jobs today, so nothing actually invokes it.

## The gap — confirmed by code, not assumption

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

## Open questions before implementing a fix

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

## Not started

No code changes have been made. `format_memory_context()`, `MemoryContext`,
and `RoutingService` are all unchanged as of this writing — this document
exists to make the gap explicit and trackable, not to record a fix.
