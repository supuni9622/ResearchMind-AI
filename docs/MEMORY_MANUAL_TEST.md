# Memory Manual Test

## M0 — Feedback-Derived Memory Transaction Isolation

Submit rating-only feedback and confirm:

- Feedback and `user_rating` eval score are stored.
- No USER memory is created.

Submit objective feedback such as “The cited paper is incorrect” and confirm:

- Feedback is classified as `objective`.
- No USER memory is created.

Submit preference feedback such as “Please keep future answers concise” and confirm:

- Feedback and eval score commit.
- A USER memory is created with `source=feedback`.
- A subsequent Chat or Research request includes it under durable preferences.

Submit the same preference again and confirm:

- It updates/deduplicates rather than creating unlimited duplicate rows.

Simulate memory database failure and confirm:

- `/feedback` still succeeds.
- Feedback and `eval_scores` remain stored.
- `feedback.preference_memory_failed` is logged.
- No broken partial USER memory remains.

## M1 — SESSION Context Ordering

Create a conversation with more SESSION memory entries than
`memory_context_session_max_items` and confirm:

- The memory block includes exactly the newest configured number of SESSION
  entries.
- Older entries outside the cap are omitted.
- Included entries remain ordered oldest-to-newest so the prompt preserves the
  sequence in which session state changed.
- The newest SESSION entry is present and is the final entry in the Active
  session state section.

Use a conversation with fewer SESSION entries than the cap and confirm:

- Every non-empty SESSION entry is included.
- Their original chronological order is unchanged.

Add ranked SEMANTIC or RESEARCH memories beyond their formatting cap and
confirm:

- Their existing best-first relevance ordering is unchanged.
- M1 affects only SESSION cap selection.

## M2 — Memory Mutation Limits and Payload Bounds

Submit personal memory creates and updates within the configured write limit
and confirm:

- Valid requests succeed and persist the intended change.
- Creates and updates consume the shared owner-scoped `memory_write` bucket.
- Memory search, context, and recall requests do not consume this bucket.
- Accepted mutations increment `memory.mutation_accepted` with the correct
  `create` or `update` operation label.

Exceed `memory_write_rate_limit_requests` within its window and confirm:

- The next create or update returns HTTP 429.
- The response includes `Retry-After` and `retry_after_seconds`.
- No database, Valkey SESSION, embedding, or Qdrant write occurs for the
  rejected request.
- `memory.mutation_rejected` is incremented with the attempted operation.

Submit deletes within and beyond the configured destructive-operation limit
and confirm:

- Deletes use the separate owner-scoped `memory_delete` bucket.
- Write-bucket traffic does not consume the delete allowance.
- An over-limit delete returns HTTP 429 before removing any memory.

Submit create and update payloads that exceed the configured content length,
metadata encoded-byte limit, or metadata nesting-depth limit and confirm:

- The API returns HTTP 422.
- No mutation limiter token is consumed because schema validation happens
  before the endpoint executes.
- No memory storage operation occurs.

Make Valkey unavailable while calling a public memory mutation and confirm:

- The mutation fails closed and does not write memory while its abuse-control
  decision is unknown.
- Existing Chat, Research, memory reads, and already stored memories remain
  usable.

Drive more eligible post-turn extractions for one owner than
`memory_extraction_rate_limit_requests` allows and confirm:

- The answer flow still succeeds.
- The extraction LLM and durable memory write are skipped after the quota.
- `memory.extraction_rate_limited` and `memory.extraction_skipped` increment.
- Another owner retains an independent extraction allowance.
- A malformed extraction response cannot persist more than
  `memory_extraction_max_memories_per_turn` rows from one turn.

Make Valkey unavailable during internal post-turn extraction and confirm:

- The internal quota check fails open so Chat or Research completion is not
  broken by the limiter dependency.
- The existing extraction failure handling remains unchanged.

## M4 — Coordinated Memory-Context Token Budget

No configuration is required for normal operation. The defaults are:

```env
MEMORY_CONTEXT_TOTAL_TOKEN_BUDGET=1200
MEMORY_CONTEXT_RESERVED_EVIDENCE_TOKENS=4000
MEMORY_CONTEXT_RESERVED_OUTPUT_TOKENS=2000
MEMORY_CONTEXT_SESSION_TOKEN_SHARE=300
MEMORY_CONTEXT_USER_TOKEN_SHARE=300
MEMORY_CONTEXT_SEMANTIC_TOKEN_SHARE=300
MEMORY_CONTEXT_RESEARCH_TOKEN_SHARE=300
```

Restart the API and Research Runtime worker after changing these settings.

For a visible local test, temporarily reduce the budget:

```env
MEMORY_CONTEXT_TOTAL_TOKEN_BUDGET=150
MEMORY_CONTEXT_SESSION_TOKEN_SHARE=40
MEMORY_CONTEXT_USER_TOKEN_SHARE=40
MEMORY_CONTEXT_SEMANTIC_TOKEN_SHARE=40
MEMORY_CONTEXT_RESEARCH_TOKEN_SHARE=40
```

Create several long USER and RESEARCH memories through `POST /api/v1/memory`,
then make a relevant request through Chat, Linear Research, Deep Research
proposal generation, and Deep Research execution. Inspect the final rendered
prompt in LangSmith and confirm:

- All four surfaces use the same bounded background-memory format.
- Selected memories are complete entries and are not cut off mid-fact.
- The complete block, including headings, precedence instructions, and the
  omission summary, stays within the configured estimated-token budget.
- The block reports omitted counts such as `user=2` or `research=3` when
  candidates do not fit.
- SESSION selection keeps the newest configured entries and renders them
  oldest-to-newest.
- USER, SEMANTIC, and RESEARCH candidates preserve their best-first order.
- Unused capacity from one type is available to higher-priority deferred
  candidates from other types.
- An explicit instruction in the current question overrides a conflicting
  durable USER preference.
- Retrieved document evidence and citations remain present and unchanged.

The `/api/v1/memory/context` endpoint returns structured memories before prompt
formatting, so it does not by itself verify M4. Use the final LangSmith prompt
or the registered metrics instead.

After a memory-aware request, inspect API metrics:

```bash
curl -s http://localhost:8000/metrics/ \
  | rg 'researchmind_memory_context_(tokens|items|budget)'
```

Confirm these series are registered and change after requests:

- `researchmind_memory_context_tokens_selected`
- `researchmind_memory_context_tokens_dropped`
- `researchmind_memory_context_items_omitted_total{type="..."}`
- `researchmind_memory_context_budget_utilization_ratio`

Run the focused automated regression as a supporting check:

```bash
DEBUG=false ENVIRONMENT=test uv run pytest \
  tests/unit/ai/memory/test_formatting.py -q
```

After manual testing, restore the normal 1,200-token total and 300-token
per-type shares, then restart the affected processes.

The lifecycle worker exposes its separately registered M3 metrics on port
`8011` by default. If testing that process alongside M4, set or retain:

```env
MEMORY_LIFECYCLE_WORKER_METRICS_PORT=8011
```

and verify:

```bash
curl -s http://localhost:8011/ | rg 'researchmind_memory_lifecycle'
```
# Personal Memory UI manual test

Use this check for the initial personal-memory slice of M12/M13. The Project
Memory panel remains informational until the Project/workspace UX supplies an
authorized project context; the M5 storage boundary is already implemented.

1. Start the API and web application, sign in, and open `/memory` from the main
   navigation.
2. If the list is empty, create a USER memory through `POST /api/v1/memory` or
   tell Chat an explicit durable preference such as “Remember that I prefer
   concise answers.” Refresh the Memory page.
3. Confirm the preference appears under **About you** and no raw SESSION
   entries appear.
4. Create more than ten USER memories and confirm the page reports an accurate
   filtered total, shows ten rows per page, and enables **Previous**/**Next**
   without duplicating or skipping records. Search for part of a memory and
   verify the result is filtered server-side. Select **From feedback** and
   verify only rows with `metadata.source=feedback` remain.
5. Select **Edit**, change the text, and save. Refresh the page and verify the
   edited value persists. Then make an eligible Chat or Research request and
   verify the corrected preference is the value injected on the next turn.
6. Select **Forget**, cancel once to verify confirmation is required, then
   confirm. Refresh and verify the item remains absent.
7. Confirm **Project memory** remains disabled pending Project/workspace
   activation and does not show or imply unscoped project data.
8. Sign in as a second user and verify the first user's memories are never
   listed, editable, or deletable.

# M5 project-scope manual test

No new environment variables are required. Apply the database migration before
starting the updated API:

```bash
uv run alembic upgrade head
```

Until the Project creation API/UI ships, create a Project and membership using
an authenticated database fixture or SQL console. Then use the normal
`/api/v1/memory` endpoints with `scope_type: "project"` and that `project_id`.

1. Create two users and two projects. Give User A membership only in Project A
   and User B membership only in Project B.
2. As User A, create one personal USER memory and one Project A memory. Confirm
   responses include the requested `scope_type` and `project_id`.
3. List and search Project A. Confirm only Project A records are returned. Ask
   for context with `inherit_personal_user_memory=true`; confirm the personal
   USER default and Project A memories are present.
4. Repeat with `inherit_personal_user_memory=false`; confirm the personal USER
   default is absent.
5. As User A, request Project B by UUID for list, search, context, edit, and
   delete. Every operation must return `403` before reading or mutating memory.
6. As User B, confirm Project A is similarly denied. Also verify a project ID
   cannot be supplied with personal scope and project scope cannot omit it.
7. Inspect a Project A SEMANTIC/RESEARCH vector in Qdrant and confirm its
   payload has `scope_type=project` and the exact Project A ID. Confirm Project
   A search cannot retrieve a Project B point.
8. Inspect Valkey after project SESSION/extraction activity and confirm keys
   include the project scope/ID, distinct from personal and Project B keys.

# M6 offline benchmark smoke test

Run the checked-in synthetic reference through the deterministic scorer:

```bash
DEBUG=false ENVIRONMENT=test uv run python -m benchmarks.memory.runner \
  --dataset benchmarks/datasets/memory/v1/dataset.json \
  --results benchmarks/datasets/memory/v1/reference-results.json \
  --output /tmp/researchmind-memory-m6-report
```

Confirm the command exits zero and creates `report.json` and `report.md`.
Inspect the JSON and verify `scope_leak_rate` and
`unsafe_memory_injection_rate` are both `0`. To exercise the release gate,
copy the result file outside the repository, add an ID not present in a query's
`allowed_memory_ids`, rerun the command, and confirm it exits non-zero. The
reference result validates the scorer only; it does not certify live retrieval.
