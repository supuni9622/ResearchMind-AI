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

## M6 authenticated staging capture

1. Seed one staging account/project/session with the logical scenarios and
   memories from `benchmarks/datasets/memory/v1/dataset.json`.
2. Copy `benchmarks/datasets/memory/v1/capture-config.example.json` to a secure
   location outside the repository. Replace every token and UUID with the
   corresponding staging value. Do not commit this file.
3. Capture and score the real API behavior:

```bash
uv run python -m benchmarks.memory.capture \
  --dataset benchmarks/datasets/memory/v1/dataset.json \
  --config /secure/path/memory-capture-config.json \
  --base-url https://your-staging-api \
  --output /tmp/memory-live-results.json

uv run python -m benchmarks.memory.runner \
  --dataset benchmarks/datasets/memory/v1/dataset.json \
  --results /tmp/memory-live-results.json \
  --output /tmp/memory-live-report
```

The second command must exit zero. Any unmapped returned UUID is deliberately
reported as a scope leak. Review `/tmp/memory-live-report/report.json`, even on
success, and preserve it as deployment evidence with the tested commit SHA and
policy version.

For answer utility, execute every dataset prompt through the same staging
generation path twice: once with memory injection disabled and once enabled.
Create `/tmp/memory-answer-pairs.json` with top-level `candidate`, `version`,
`dataset_version`, and a `pairs` array containing `query_id`,
`answer_without_memory`, and `answer_with_memory` for every query. Then run:

```bash
OPENAI_API_KEY=... uv run python -m benchmarks.memory.answer_utility \
  --dataset benchmarks/datasets/memory/v1/dataset.json \
  --pairs /tmp/memory-answer-pairs.json \
  --output /tmp/memory-answer-utility
```

Human-review a sample before treating judge results as a release signal. To
store the per-query retrieval or answer-utility metrics in `eval_scores`, run
`uv run python -m benchmarks.memory.persist_scores --report <report.json>`
against the intended environment database.

## M7 trace correlation and explicit feedback

1. Apply the latest database migration and run the API, web app, and evaluation
   worker:

```bash
uv run alembic upgrade head
uv run python -m apps.worker.eval_scoring_main
```

2. Ensure the signed-in user has a relevant durable memory, then ask a new Chat,
   Linear Research, or Deep Research question that retrieves it. For Deep
   Research, approve the plan and complete the report flow. Once the answer completes,
   verify “Memory helped” and “Memory was wrong” appear below the normal answer
   feedback. They must not appear for an answer that injected no memory.
   Deep Research receives this boolean from the owner-authorized final-report
   lookup for approved PDF reports, or from the owner-scoped session replay for
   a report rejected and published as a plain answer. Test both approval choices.
   The API never exposes the underlying memory UUIDs to the browser.
3. Click “Memory helped,” refresh, then inspect PostgreSQL. The generation's
   `generation_usage.injected_memory_ids` must be non-empty; `memory_feedback`
   must contain an owner-scoped `helped` row; and `eval_scores` must contain
   `metric_name=memory_user_signal`, `source=human_feedback`, `score=1`.
4. Change the signal to “Memory was wrong.” Confirm the same row is updated,
   not duplicated, and the mirrored score becomes `0`. Attempt the endpoint as
   another owner and confirm it returns `404` without revealing whether the
   generation exists.
5. To test sampled scoring, set the following in the evaluation-worker
   environment and restart it:

```bash
MEMORY_ONLINE_UTILITY_JUDGE_ENABLED=true
EVAL_ONLINE_BASELINE_SAMPLE_RATE=1.0
```

Use `1.0` only for a short staging test. Confirm sampled memory-backed
generations receive `memory_utility` and `irrelevant_memory_harm` rows. Their
reasons must remain categorical and must not contain raw memory content. Return
the sample rate to its normal value after the test.

## M8 semantic/research consolidation

M8 runs inside the existing memory lifecycle worker and is off by default.
First create two similar SEMANTIC or RESEARCH memories for the same owner and
scope, plus a deliberately contradictory pair. Start in report-only mode:

```bash
MEMORY_CONSOLIDATION_ENABLED=true \
MEMORY_CONSOLIDATION_DRY_RUN=true \
uv run python -m apps.worker.memory_lifecycle_main
```

Confirm `memory.consolidation.dry_run_decision` logs contain only IDs and a
typed action, never memory content. Review a representative sample and run the
M6 retrieval benchmark. Only after the decisions are acceptable, temporarily
set `MEMORY_CONSOLIDATION_DRY_RUN=false` in staging. Duplicate/mergeable pairs
must leave one active canonical result; the source row must still exist in
Postgres with `_consolidated_into`, and the canonical row must contain its ID
in `_merged_from`. Contradictory and unrelated rows must remain independently
retrievable. Simulate a Qdrant failure and confirm neither Postgres row is
archived. Return the feature to dry-run or disabled after the staging check.

## M9 dormant preference supersession

1. Create a USER preference such as “Prefer concise answers,” then create at
   least 20 newer preferences on unrelated topics so the original is outside
   the former recency window.
2. Submit “Prefer detailed answers.” Confirm the old row is updated in place,
   not duplicated, and its metadata contains `preference_key` plus
   `_supersession.replaced_memory_id`, `reason`, and `decided_at`.
3. Create two related but distinct preferences, such as “Use concise answers”
   and “Use APA citations.” Confirm both remain present; topic nomination must
   never be treated as overwrite authority.
4. Repeat with project scope and confirm only the selected project's memories
   are candidates. Repeat as another owner and confirm no cross-owner update.
5. Temporarily make the topic classifier unavailable. The new preference must
   still be created; logs may report classification failure, but the user flow
   must not fail.
6. Run the M6 v1.1 benchmark and require the existing Recall@5 and isolation
   gates to remain green.
