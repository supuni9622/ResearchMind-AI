# ADR-030 — Chat History Pagination and Context Compaction

**Status:** Accepted  
**Date:** 2026-07-19

---

# Context

Chat messages are canonical PostgreSQL records and a conversation can grow
without a practical upper bound. Previously, the Chat read path used a fixed
history limit. That protected the API and generation prompt from unbounded
payloads, but it had two undesirable effects:

- older messages could disappear from the UI/API response without an explicit
  way to retrieve them; and
- passing all historical messages to a model would eventually increase token
  cost and latency, even when most of the transcript was no longer relevant.

The solution must preserve the full audit/replay record, allow a user to load
older material deliberately, and keep generation context bounded without
adding another LLM call on the answer path.

---

# Decision

Use cursor pagination for persisted Chat history and deterministic rolling
compaction for model prompt history.

## Pagination

The Chat API exposes cursor-based pages for both conversation summaries and
messages:

- `GET /api/v1/chat/conversations?cursor=<conversation-id>&limit=<n>`
- `GET /api/v1/chat/conversations/{conversation_id}?cursor=<message-id>&limit=<n>`

Responses include `next_cursor`. The frontend initially renders the newest
page and shows an explicit control to load older conversations or messages.
Pages are owner-scoped, ordered chronologically for display, and fetched using
the stable `(created_at, id)` / `(updated_at, id)` ordering in the repository.
This avoids offset-pagination drift when newer rows are added concurrently.

Canonical message rows are never removed or overwritten by compaction. The
pagination API is the replay path for all original content.

## Prompt-history compaction

Before a Chat generation, the application keeps the most recent persisted
messages verbatim and replaces older prompt history with a compact,
deterministic summary. The summary is stored on the `conversations` row with a
timestamp marking the newest message it covers:

- `history_summary`
- `history_compacted_through_at`

On a later turn, only messages after that boundary are considered for the next
rolling compaction. The prompt contains, in order:

1. the persisted summary of older history;
2. the newest verbatim messages; and
3. the current user prompt.

The compactor is intentionally not an LLM. It normalizes whitespace, records
bounded user/assistant turn excerpts, and places explicit user-interest,
preference, and decision phrases first. That makes compaction incremental,
predictable, and zero-provider-cost. Durable-memory promotion remains a
separate policy governed by ADR-029; compaction is not a substitute for
semantic or user-profile memory.

---

# Initial Defaults and Their Basis

The following settings live in `apps/api/app/core/settings.py` so operators can
tune them without changing request or persistence contracts.

| Setting | Initial value | Purpose and rationale |
| --- | ---: | --- |
| `chat_history_page_size` | 50 | A practical first UI/API page: enough surrounding context for replay while keeping normal response payloads small. |
| `chat_history_page_max_size` | 100 | A server-enforced upper bound that permits a larger deliberate fetch without allowing an accidental unbounded query. |
| `chat_prompt_recent_message_limit` | 12 | Retains several recent multi-turn exchanges verbatim, where follow-ups most often depend on exact wording, while capping repeat prompt growth. |
| `chat_prompt_summary_max_characters` | 4,000 | Bounds the older-history representation to a modest, predictable amount of prompt text and database storage per conversation. |

These are conservative starting values, selected from the application’s
existing fixed 50-message history behavior and the need to preserve a useful
recent-turn window. They are configuration defaults, not claims of an already
measured universal optimum. They should be adjusted only after observing
production/staging metrics such as page payload size, prompt token counts,
generation latency, compaction frequency, and user use of “load earlier”.

---

# Runtime Behavior

1. A user opens a conversation: the API returns the newest page and, if older
   data exists, a `next_cursor`.
2. Selecting **Load earlier messages** sends that cursor and prepends the
   resulting canonical rows to the view. The same pattern applies to the
   conversation sidebar.
3. Before the next response is generated, Chat checks the messages that have
   not already been represented by `history_summary`.
4. If more than 12 are available, all but the newest 12 are folded into the
   bounded summary and the compaction boundary advances transactionally.
5. Generation receives the summary plus the newest 12 messages, rather than
   the entire transcript. Memory retrieval receives this bounded transcript as
   well.
6. A database, pagination, or compaction failure must not delete historical
   rows. Standard request failure handling remains in effect; compaction does
   not call an external provider.

---

# Consequences

## Positive

- Full Chat history remains available without loading unbounded data by
  default.
- Model input stays bounded as a conversation grows, reducing repeated prompt
  tokens and latency.
- The implementation adds no summarization-model dependency, provider
  fallback, or extra generation-usage cost.
- Explicit preferences and decisions receive preferential retention in older
  context.
- Persisting the compaction boundary makes repeated compaction incremental
  rather than rebuilding from the entire conversation each turn.

## Trade-offs

- A deterministic summary is less nuanced than a model-written summary and
  may omit details that are not marked as explicit preferences/decisions or
  captured by turn excerpts.
- The 12-message and 4,000-character defaults require real-traffic tuning;
  different conversation styles may need different values.
- The current scope is Chat only. Research Runtime has its own future context
  strategy and must adopt compatible pagination/compaction deliberately rather
  than inheriting this behavior implicitly.

---

# Alternatives Considered

## Keep a fixed hidden history limit

Rejected: it makes older messages appear unavailable and does not provide a
safe replay mechanism.

## Send the full transcript on every generation

Rejected: cost and latency grow with every turn and eventually exceed provider
context limits.

## Use an LLM to summarize on every compaction

Deferred: it can improve narrative quality but creates another provider call,
fallback path, latency source, and cost centre. The deterministic summary is
the appropriate production baseline; evaluate an optional background,
versioned LLM-summary upgrade only when telemetry demonstrates it is needed.

## Delete compacted messages

Rejected: destructive compaction would weaken user replay, debugging,
auditing, and future re-compaction strategies.
