# ADR-031 — Research Runtime Boundary

**Status:** Accepted  
**Date:** 2026-07-19

## Decision

ResearchMind owns canonical Research Runtime contracts, lifecycle records,
policies, artifacts, public events, authorization, and memory boundaries.
LangGraph is used only for execution mechanics: graph scheduling, checkpoint
integration, interrupts, and later fan-out.

The Phase 1 graph is a disabled deterministic walking skeleton. It is not
wired to the existing linear `/research` API and does not call providers,
retrieval, artifacts, or memory services.

## Consequences

- Existing linear Research behavior remains the production fallback.
- Graph state is compact, JSON-safe, and contains no documents, embeddings,
  provider responses, or canonical reports.
- Only a future finalization boundary may call `MemoryExtractionOrchestrator`,
  after the final user-facing answer is persisted.
- Planner, retrieval, reviewer, retry, and helper nodes are ineligible to
  create durable memory or memory-extraction usage.

## Status update (2026-07-23)

The "Phase 1 graph ... is not wired to the existing linear `/research` API"
statement above described the state at 2026-07-19 and is now historical, not
current. An approval-gated Deep Research path (proposal → approval → durable
run → dedicated-worker graph execution → SSE events → report) has since been
built and is live; see **ADR-034** for the routing decision, the current
architecture, and its documented open gaps. The linear `/research` and
`/research/stream` routes themselves are unaffected and remain the
unconditional default, per ADR-034.
