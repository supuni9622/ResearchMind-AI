# TODO: Short-circuit retrieval on cache hit for Linear Research (L1)

**Status:** Not started — needs more investigation before implementation.
**Source:** `PRODUCT_FLOWS_AND_GAPS.md`, Loophole L1 (Linear Research section) /
priority list item 3. Re-verified against code on 2026-07-26.

## The gap

`ResearchService.research()` and `.stream_research()` call
`_retrieve_and_build_context()` (embedding + Qdrant hybrid search + context
build) **unconditionally**, before the `GenerationRequest` is even built:

- `apps/api/app/ai/research/service.py:169-174` (`research()`)
- `apps/api/app/ai/research/service.py:322-327` (`stream_research()`)

Caching (`CacheRuntime.RESEARCH`, `CachePolicy.AUTO`) only applies inside
`GenerationRuntime.execute()` / `StreamingService`, which runs strictly after
retrieval has already completed. So a repeat or near-duplicate question pays
full retrieval cost (embedding call + Qdrant query) every time, even when the
eventual answer would have been an exact-cache hit — caching only ever saves
the generation-provider call.

## Why it's not a simple reorder

The exact-cache key is built from **post-retrieval** state:

`apps/api/app/ai/runtime/generation/caching/exact/key_builder.py:81-83` —
`context_hash = hash_context(request.prompt_context.context)`, i.e. the
fully-rendered retrieval output itself. This is deliberate (see
`caching/create.py`'s comment and `PRODUCT_FLOWS_AND_GAPS.md`'s X3 section):
it's what guarantees a genuinely different document context can't collide
with a stale cached answer. That means the current cache key literally
cannot be computed until after retrieval has already run.

## Pros of making the change

- Real, recurring savings on the actual bottleneck for repeat/near-duplicate
  traffic — skips the embedding-provider call and the Qdrant round-trip, not
  just the generation call.
- Reduces load on the retrieval backend under bursty/looping usage (pairs
  well with the existing per-owner rate limiter).
- For byte-identical repeats (true exact-cache hits), there's no scenario
  where retrieval could have produced something different — a pure win with
  no correctness cost, if it can be made to work at all.

## Cons / risks

- **Chicken-and-egg key problem**: checking cache before retrieval requires
  a different, retrieval-independent key (e.g. raw query + filters +
  owner_id). That reopens the exact collision risk the current design
  prevents — two different document corpora producing the same "cached"
  answer.
- **Concrete staleness risk**: a user uploads a new document, then re-asks a
  previously-cached question — a naive pre-retrieval cache check would serve
  the old answer/citations, silently ignoring the new document. Needs a fast
  corpus-freshness signal (e.g. a per-owner ingest counter/version bumped on
  upload) folded into the pre-check key — new invalidation state to build
  and get right, not just a reordering of existing calls.
- **Semantic (AUTO) cache makes this worse**: its entire value is fuzzy
  matching on *meaning* across non-identical transcripts. Skipping retrieval
  on a semantic near-hit means trusting that a different question would have
  retrieved the same chunks — exactly the thing only retrieval can confirm.
  Materially bigger correctness risk than the exact-cache case.
- **Architectural friction**: caching today lives entirely inside
  `GenerationRuntime.execute()` / `StreamingService`, one layer below where
  retrieval happens in `ResearchService`. A pre-check means either
  duplicating cache-lookup logic in `ResearchService` (two places that must
  agree on cache semantics) or re-plumbing `GenerationRuntime` to defer
  context-building — a nontrivial refactor either way.
- **Miss-path latency regression**: on a cache miss (the common case for
  genuinely novel queries), the pre-check itself adds a small extra
  round-trip in front of retrieval that doesn't exist today.

## Leaning recommendation (not decided)

Scope to the **exact-cache path only**, gated behind a cheap per-owner
corpus-version stamp so a hit can't paper over newly-ingested documents.
Leave the semantic/AUTO cache paying full retrieval cost — the fuzzy-match
correctness risk isn't worth the savings, and exact hits are likely the more
common "same question again" case this is meant to address anyway.

## Open questions before implementing

- What should the corpus-freshness signal be, and where does it get bumped
  (document upload, delete, reprocess)?
- Does this belong in `ResearchService`, or does `GenerationRuntime` need a
  way to expose "would this be a cache hit" without a full `execute()` call?
- Is the miss-path latency cost (one extra cache lookup round-trip) acceptable
  given novel queries are presumably the majority of traffic?
- Should this also apply to `citations_only()` (`/research/citations`), which
  currently always retrieves too, or is that out of scope since it never
  generates/caches at all?
