# ADR-035 — Generation Reliability: Groq Tool-Call Enforcement and Regeneration Token-Budget Self-Healing

**Status:** Accepted
**Date:** 2026-07-24
**Related ADRs:** ADR-024 (Generation Model Strategy), ADR-026 (Model Routing Platform),
ADR-031 (Research Runtime Boundary)

---

## Context

The Deep Research flow (planner → retrieval → synthesis → review, see ADR-031/ADR-034)
repeatedly failed in production with schema-invalid structured output, requiring the same
class of bug to be hand-fixed more than once:

1. **`ResearchPlannerError("Planner did not return a schema-valid plan.")`**
   (`apps/api/app/ai/runtime/research/planner/service.py`), reproduced with the **groq**
   provider. Root cause: Groq's native `response_format: json_schema` (schema-constrained
   decoding) is only enabled for a narrow, Groq-curated model allowlist that excludes
   `llama-3.3-70b-versatile` — this platform's default/AUTO-routed Groq model (`RoutingService`
   hard-prefers groq for `RoutingStrategy.AUTO`). Every Groq `STRUCTURED` request therefore fell
   back to plain `{"type": "json_object"}` mode (`build_groq_response_format()` in
   `apps/api/app/ai/runtime/generation/providers/helpers/structured.py`) — **zero schema
   enforcement**, relying only on the schema being spelled out as prose in the prompt. Against
   `ResearchPlan`'s constraints (`task_id` regex, enums, cross-field validation, exactly-one-task
   when `execution_strategy == FOCUSED`), the model would occasionally drift even after the one
   regeneration attempt. OpenAI and Claude never hit this because they get real schema-constrained
   decoding from their providers directly.

   A prior attempt to fix this by sending Groq native `response_format: json_schema` anyway
   (commit `9a6abd4`) was reverted (commit `f3c13e8`) because `llama-3.3-70b-versatile` returns a
   400 for that request shape. That revert left the model with no enforcement mechanism at all.

2. **`ResearchSynthesisError("Synthesis did not return a schema-valid draft.")`**
   (`apps/api/app/ai/runtime/research/synthesis/service.py`), reproduced with the **claude**
   provider — i.e. a different, provider-agnostic root cause. `ResearchSynthesisService.synthesize()`
   hardcoded `max_tokens=2_000` for the `ResearchDraft` output schema
   (`apps/api/app/ai/runtime/research/synthesis/models.py`), which permits a fully-populated draft
   of up to ~60,000+ characters (title + abstract + methodology + up to 8 `findings` sections of up
   to 6,000 characters each + discussion + conclusion + limitations) — roughly 15,000–18,000 tokens
   worst case. 2,000 tokens is an order of magnitude too small. Observed failure:
   `finish_reason='max_tokens'`, `completion_tokens` exactly equal to the cap, content cut off
   mid-JSON so parsing failed even with repair, `parsed_output=None`, cascading through every
   output/runtime completeness validator, regenerating and truncating again identically, and
   finally raising. This is the same *shape* of bug the planner had already hit once — its own
   `max_tokens` had previously been bumped from 800 to 2,000 for the same reason (see the comment
   already in `planner/service.py`) — recurring one runtime stage later against a much larger
   schema.

Both bugs were fixed at their specific call sites, but fixing each instance by hand as it was
discovered does not prevent a **third** occurrence: any future runtime stage, schema change, or
evidence-volume growth can under-size a hardcoded `max_tokens` again, and the existing
regeneration mechanism (`GenerationService._build_corrected_request()`) made this worse, not
better — it retried a truncated attempt with an unchanged system prompt and the *identical*
`max_tokens`, so a truncation-caused failure reliably truncated again the same way. Hand-sizing
every call site's budget forever, and hoping regeneration would organically recover, had already
silently failed twice.

## Decision

### 1. Groq structured output uses forced tool-calling, not `json_object` mode

`apps/api/app/ai/runtime/generation/providers/groq.py` now builds a forced single tool call
(`tool_choice` naming one function whose `parameters` *is* the request's output schema) instead
of `{"type": "json_object"}` whenever `response_format == STRUCTURED` and an `output_schema` is
present. Groq's tool/function-calling is broadly supported — unlike the narrow Structured Outputs
allowlist — and the model is fine-tuned to follow function-call argument schemas precisely, which
constrains the response shape far more reliably than prompt-only JSON mode. `generate()` reads
`tool_calls[0].function.arguments` back as `content` when a forced call is present, falling back
to `message.content` otherwise. This is purely internal to the Groq provider: it does not set
`request.tools`, so it is invisible to `RequiredCapability.TOOL_CALLING` routing/validation and
does not require changing the (separately inaccurate) `tool_calling=False` capability flag on
Groq's `ModelMetadata` catalog entries.

### 2. Call-site `max_tokens` budgets are sized from the schema's actual bounds

`ResearchSynthesisService.synthesize()`'s `max_tokens` was raised from `2_000` to `20_000` —
comfortably above `ResearchDraft`'s theoretical worst-case size, with margin for JSON overhead.
This does not increase typical cost or latency: providers stop generating once their actual
response is complete, so the cap only removes the artificial early cutoff. Both `claude-sonnet-5`
(200k context) and the Groq models used for the `RESEARCH` runtime (131k context) have ample
headroom for a 20,000-token completion alongside typical prompt sizes (~3,000–4,000 tokens
observed).

### 3. Regeneration self-heals from truncation, independent of any one call site's budget

`GenerationService._build_corrected_request()` (`apps/api/app/ai/runtime/generation/service.py`)
now inspects the failed attempt's `result.finish_reason`. If it is in the (newly shared)
`TRUNCATION_FINISH_REASONS` constant — `"length"` (OpenAI/Groq) or `"max_tokens"` (Claude), moved
from a private constant inside `ResponseSizeValidator` into `app/ai/runtime/generation/models.py`
so both consumers agree on what "truncated" means — the regenerated request's `max_tokens` is
doubled, capped at `_REGENERATION_MAX_TOKENS_CEILING = 32_000`. The corrective system-prompt text
was also split by cause: a truncated response now gets "you were cut off before finishing, you
have more room now" instead of the previously blanket (and, for this cause, inaccurate) "your JSON
was malformed" instruction.

This only escalates on an explicit truncation signal — an ordinary schema/parse failure (wrong
enum value, extra key, fabricated citation) retries with the same `max_tokens` unchanged, since
more tokens would not fix those. The 2x-per-attempt multiplier and the absolute ceiling bound the
cost/latency impact; `max_regeneration_attempts` is 1 almost everywhere in the research runtime
today, so in practice this fires at most once per generation call. Every current provider's
context window (131k–200k tokens) comfortably fits a 32,000-token completion alongside typical
prompt sizes.

## Consequences

**Positive:**

- An under-sized `max_tokens` at *any* current or future call site — not just the planner and
  synthesis stages fixed here — now degrades to one extra regeneration round-trip instead of a
  hard `ResearchPlannerError` / `ResearchSynthesisError` / equivalent failure. This is a structural
  fix to the class of bug, not another instance-specific patch.
- Groq's structured output reliability for `RESEARCH`/`PLANNER` runtimes no longer depends on
  Groq eventually adding `llama-3.3-70b-versatile` to their native Structured Outputs allowlist.
- `generation.regeneration.max_tokens_escalated` is logged whenever the escalation path fires,
  giving direct observability into how often call sites are under-budgeted in practice — useful
  signal for correcting a call site's *initial* budget rather than relying on the escalation path
  indefinitely.

**Negative / accepted trade-offs:**

- The escalation path adds one full extra provider round-trip (latency + cost) on top of whatever
  `max_regeneration_attempts` already budgeted, in the case where it fires. This is strictly better
  than a hard failure, but still worse than sizing the initial `max_tokens` correctly, so callers
  should still size budgets from the output model's actual `Field(max_length=...)`/`max_length`
  bounds rather than relying on this as a first line of defense.
- The Groq forced-tool-call mechanism is Groq-specific internal plumbing (a second structured-
  output code path alongside `build_groq_response_format()`'s `json_object` mode, used for
  non-STRUCTURED / no-schema requests). If Groq's native Structured Outputs allowlist later
  includes the models this platform routes to, the forced-tool-call path could be replaced with
  native `json_schema` mode — there is no strong reason to do so preemptively, since tool calling
  already works.
- `_REGENERATION_MAX_TOKENS_CEILING` (32,000) and the 2x multiplier are fixed constants, not
  derived per-model from `ModelMetadata.context_window` or a provider's actual max-output-token
  limit. If a future provider/model has a materially smaller output-token ceiling than today's
  three (OpenAI, Claude, Groq), this escalation could itself request more tokens than that
  provider allows. No such provider is in the catalog today.

## What this does not cover

- Non-truncation schema-invalid failures (a model producing well-formed but semantically wrong
  JSON — e.g. a fabricated citation ID, a wrong enum value) are unaffected by this ADR; they were
  already handled by the existing corrective-feedback regeneration path and still are.
- This ADR does not change `max_regeneration_attempts` defaults anywhere; it only changes what a
  regeneration attempt looks like when the prior attempt was truncated.
- Gemini and Ollama providers do not currently populate `finish_reason`, so the escalation path is
  presently a no-op for those two until their provider adapters are updated to report it.
