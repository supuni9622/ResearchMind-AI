# LangSmith Tracing

**Status:** Implemented (Generation runtime only)
**Related:** `oberservability_platform_prd.md` §11-12, §17

---

## What LangSmith Owns Here

Per the observability PRD's architectural philosophy, ResearchMind does not
rebuild tracing/experiment/dataset infrastructure — LangSmith owns request
traces, run trees, and span visualization. ResearchMind owns metrics,
statistics, reports, and artifacts, and feeds LangSmith trace metadata/tags.

Only the tracing piece (§11.1) is implemented today. Dataset (§11.2),
experiment (§11.3), and comparison (§11.4) integration are not yet built.

---

## Configuration

Four settings in `app/core/settings.py`, sourced from env vars:

| Env var | Settings field | Default | Purpose |
|---|---|---|---|
| `LANGSMITH_API_KEY` | `langsmith_api_key` | `None` | Auth for the LangSmith client |
| `LANGSMITH_TRACING` | `langsmith_tracing` | `False` | Explicit opt-in to send traces |
| `LANGSMITH_ENDPOINT` | `langsmith_endpoint` | `None` | `Client(api_url=...)` — usually `https://api.smith.langchain.com` |
| `LANGSMITH_PROJECT` | `langsmith_project` | `"ResearchMind"` | LangSmith project name traces are grouped under |

**Both `langsmith_api_key` and `langsmith_tracing` must be set** for tracing
to activate — see `_langsmith_enabled()` in
`app/ai/observability/providers/langsmith/create.py`. This lets ops keep the
key configured in the environment while switching tracing off locally
without unsetting it. An API key alone does **not** enable tracing.

If either is missing, `create_runtime_tracer()`/
`create_langsmith_metrics_recorder()` return `NoOpTracer`/
`NoOpMetricsRecorder` — zero behavior change, zero network calls.

---

## How It's Wired

```
app/ai/observability/providers/langsmith/
    client.py    get_langsmith_client() -- lazy, cached langsmith.Client factory
    tracing.py   RuntimeTracer (ABC), NoOpTracer, LangSmithTracer
    recorder.py  LangSmithMetricsRecorder (MetricsRecorder impl)
    create.py    create_runtime_tracer(), create_langsmith_metrics_recorder()
```

`GenerationService` (`app/ai/runtime/generation/service.py`) takes an
optional `tracer: RuntimeTracer` constructor param, defaulting to
`NoOpTracer()`. In `_execute_once()` (used by the non-streaming `generate()`
path), the provider call is bracketed:

```python
with self._tracer.trace(
    name="generation",
    inputs={"prompt": request.user_prompt},
    tags={"provider": provider.value, "model": ..., "runtime": ...},
) as trace_handle:
    result = await generation_provider.generate(...)
    trace_handle.set_output(
        content=result.content,
        prompt_tokens=result.statistics.prompt_tokens,
        completion_tokens=result.statistics.completion_tokens,
        total_tokens=result.statistics.total_tokens,
    )
```

`inputs` is the real prompt (shows in LangSmith's Input panel); `tags`
land under `extra.metadata` in LangSmith, not `inputs` — see "Input/Output/
Token Content" below for why that distinction matters.

The streaming path (`stream_generate()`) is **not** traced from inside
`GenerationService` itself — it calls `generation_provider.stream(...)`
directly with no wrapping. Instead, `StreamingService._stream_live()`
(`app/ai/runtime/generation/streaming/service.py`) wraps its own call into
`generation_service.stream_generate(...)` with the identical tracer:

```python
with self._tracer.trace(
    name="generation",
    inputs={"prompt": request.user_prompt},
    tags={"provider": ..., "model": ..., "runtime": ..., "streamed": True},
) as trace_handle:
    async for chunk in self._generation_service.stream_generate(...):
        ...
    trace_handle.set_output(content="".join(content_parts))
```

`StreamingService` gets this same tracer instance (not a second one) via
`generation_service.tracer` — see `streaming/create.py`. This split exists
because `/research/stream` (the route the frontend actually calls) goes
through `StreamingService`, not `GenerationService.generate()`; an earlier
version of this integration only instrumented `generate()`/`_execute_once()`
and silently produced zero traces for every streamed request until this was
caught by testing against the real frontend flow (see
`oberservability_platform_prd.md` §17 "Streaming Wiring Fix").

`LangSmithTracer.trace()` calls `Client.create_run(...)` / `update_run(...)`
directly (not the `@traceable` decorator) and stores the run id in a
`ContextVar` (`current_run_id`), which `LangSmithMetricsRecorder` reads to
attach `create_feedback()` scores to the active trace — decoupling the two
collaborators without a direct reference between them.

`app/ai/runtime/generation/create.py::create_generation_service()` wires the
real `create_runtime_tracer()` in production; nothing else needs to know
whether LangSmith is configured. `streaming/create.py::create_streaming_service()`
reuses that same instance from `generation_service.tracer`.

**Scope**: both Generation runtime entry points (streaming and
non-streaming) are traced. Retrieval, Research, and Agent runtimes are not
yet instrumented — reuse `RuntimeTracer`/`create_runtime_tracer()` rather
than building a second tracer abstraction when that's needed.

---

## Input/Output/Token Content

Earlier, `trace()` only accepted `tags`, which `LangSmithTracer` passed
straight through as `create_run(inputs=tags or {}, ...)` — the metadata
dict (provider/model/runtime) masqueraded as the actual prompt, and
`update_run()` never got an `outputs` argument, so every trace showed "No
outputs" and Monitoring's Cost/Tokens/Latency charts had nothing to
compute from (LLM Count still worked since that's just counting runs).

Fixed: `trace()` now takes a real `inputs` dict (the prompt) separately
from `tags`, and its context manager yields a `TraceHandle` with
`set_output(*, content=None, prompt_tokens=None, completion_tokens=None,
total_tokens=None)` for the caller to call once the result is known, before
the trace closes:

- `inputs` → `create_run(inputs=...)` — real Input panel content.
- `tags` → `create_run(extra={"metadata": {...}})`, additionally
  duplicating `provider`/`model` as `ls_provider`/`ls_model_name` — the
  specific keys LangSmith's own cost calculator looks for to auto-price
  well-known models. **This is LangSmith's documented convention, not
  something verified against a live account in this environment** — if
  Cost & Tokens still show nothing after this change, the model name
  string (`claude-sonnet-5`, etc.) likely doesn't match one LangSmith
  recognizes, and that's a LangSmith-side mapping issue, not a bug here.
- `set_output(...)` → `update_run(outputs={"content": ..., "usage_metadata":
  {"input_tokens", "output_tokens", "total_tokens"}})` — real Output panel
  content and the token-accounting shape LangChain/LangSmith use.

Streaming traces get `content` but not token counts in `set_output()` —
`StreamingService._build_stream_result()`'s token counting happens *after*
the trace closes (deliberately kept outside the traced try/except, so a
counting failure behaves the same as before this change rather than
turning into a synthetic stream error after real content already reached
the client).

---

## Failure Behavior

Every LangSmith call is wrapped try/except-log-swallow
(`observability.langsmith.client_unavailable` on client construction
failure). Tracing is best-effort per PRD §13 — a LangSmith outage, bad key,
or network failure never fails generation.

---

## Verifying It Works

1. Set `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true`, `LANGSMITH_ENDPOINT`,
   `LANGSMITH_PROJECT` in `.env` and restart the API (`./scripts/dev.sh`).
2. Call `POST /research/stream` with a real query (this is the route the
   frontend actually uses — `POST /research`, the non-streaming variant, is
   a separate code path and traces independently of this one).
3. Open the LangSmith project (default project name `ResearchMind`) at
   https://smith.langchain.com and confirm a run named `generation` appears
   with `provider`/`model`/`runtime` tags matching the request.
4. Watch server logs for `observability.langsmith.client_unavailable` — its
   absence, combined with the run appearing, confirms the client
   constructed and authenticated correctly.
5. To confirm the no-op fallback still works (regression check), unset
   `LANGSMITH_TRACING` and repeat step 2 — the request should succeed
   identically with no LangSmith calls.

Unit coverage: `tests/unit/ai/observability/providers/langsmith/test_create.py`
asserts the dual-gate (key alone, tracing-flag alone, and both-unset all
stay no-op; only both-set activates the real tracer/recorder).
