# ADR-029 — Cost-Aware Durable Memory Promotion

**Status:** Accepted  
**Date:** 2026-07-19

---

# Context

ResearchMind originally performed LLM memory extraction after every completed
Chat and Research turn. This maximized recall, but made an inexpensive
question such as “What is RAG?” capable of causing a provider call and a
durable profile write. The result was unnecessary spend, post-turn work,
duplicate/noisy memories, and user profiles based on weak evidence.

Removing extraction completely would solve the cost problem but would also
lose genuinely useful preferences, research goals, and durable findings.

The system needs to preserve high-value memory creation while keeping the
normal path fast, private, and inexpensive.

---

# Decision

Use a deterministic eligibility gate before LLM extraction. The LLM remains
the final validator and classifier of durable memory; it is no longer called
for every completed turn.

## Immediate eligibility

The following are eligible immediately:

- explicit memory requests, such as “remember this”;
- explicit durable preferences, instructions, decisions, goals, or research
  findings;
- explicit learning/research-interest statements, such as “I am learning
  RAG” or “I am building a RAG application.”

## Repeated-topic promotion

A generic question remains a non-durable conversational turn initially.
ResearchMind extracts at most three bounded lexical topic candidates and
records the current server-side conversation/research session ID in a
Valkey set per owner/topic. Topic text is hashed in the key.

When a topic appears in two distinct sessions, it is eligible for **one** LLM
validation. A second hashed Valkey claim key prevents subsequent sessions from
repeating the same promotion for 90 days.

The LLM receives the repeated-topic evidence and can either return a durable
`USER` interest memory or no memory. It must not infer response preferences
from the assistant's own prior answer.

## Storage and failure behavior

- `USER` and `RESEARCH` extraction results are persisted in PostgreSQL, the
  canonical durable-memory store.
- `RESEARCH` memories are also indexed in Qdrant for semantic recall; `USER`
  profile memories remain a PostgreSQL profile store.
- SESSION state is compact Valkey state only; raw Q/A duplicates are disabled
  by default because canonical Chat/Research history already persists them.
- Extraction, interest tracking, and durable writes are best effort. A
  Valkey, provider, or memory-store failure must never fail the user answer.

## Idempotency and observability

Idempotency uses canonical Chat assistant-message IDs or Research IDs plus
policy version `v2`. Structured decision/outcome events and the owner-scoped
generation usage ledger record the extraction path, including
`memory_extraction` cost.

---

# Consequences

## Positive

- Prevents a provider call and durable write for most trivial or one-off
  questions.
- Retains LLM judgment where profile quality matters.
- Allows a genuinely repeated interest to become durable without requiring an
  explicit “remember” command.
- Bounds repeated-topic extraction cost to one validation per owner/topic per
  retention window.
- Improves privacy and relevance by reducing unnecessary provider exposure and
  prompt-memory noise.

## Trade-offs

- The lexical candidate stage is intentionally conservative and may not join
  differently worded but semantically equivalent topics.
- The distinct-session counter begins after deployment; it does not backfill
  historical conversations.
- A promoted topic can still produce no PostgreSQL row when the LLM judges it
  non-durable. This is an expected outcome, not a write failure.
- The policy requires staged observation to tune the session threshold and
  retention period using skip rate, empty extraction rate, latency, and cost
  per 100 answer turns.

---

# Alternatives Considered

## Extract after every turn

Rejected: highest recall, but unacceptable cost, latency, privacy exposure,
and profile-noise rate.

## Never infer interests

Rejected: preserves cost but loses useful long-running research personalization.

## Persist every question directly as a USER memory

Rejected: makes one-off curiosity indistinguishable from a durable interest
and bypasses LLM validation.

## Semantic topic clustering on every turn

Deferred: it would improve matching of paraphrases but adds embedding/vector
work to every turn. The bounded lexical gate is the appropriate production
starting point; revisit only after staged metrics justify the added cost.
