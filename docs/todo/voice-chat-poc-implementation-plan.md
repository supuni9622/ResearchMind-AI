# Voice-on-Chat POC — Development Plan & Traceability

**Status:** planned, not started. **Driver:** interview-prep hands-on build, not a
roadmap-sequenced initiative — see "Relationship to the roadmap" below before
reading this as a Wave item. **Scope:** one surface (Chat), one vendor pair
(Deepgram STT + ElevenLabs TTS), ~1 week.

---

## 1. Purpose

Build a real, working streaming-voice slice on top of the existing Chat
surface — not a throwaway demo — to have genuine hands-on experience with
streaming STT/TTS, real-time transport, and voice-specific latency/reliability
concerns ahead of a Senior AI Engineer interview whose JD explicitly lists
voice as a delivery channel alongside chat/WhatsApp/email.

The build is deliberately scoped so that **the interesting engineering
decisions (dialogue management, RAG, guardrails, latency budgeting) are real**,
even though the surface area (one channel, one conversation mode) is
intentionally small.

## 2. Relationship to the roadmap

[`PRIORITIZED_ROADMAP.md`](../PRIORITIZED_ROADMAP.md) places Voice in **Wave
6**, after Waves 2-5 (personalization, Projects/North Star foundations,
Vision, Graph RAG/Canvas), scored `Value: Med`, `Ease: Very Low` — the worst
ease score on the roadmap, confirmed via repo search to have **zero existing
scaffold** (no STT/TTS dependency anywhere, `WS /chat/ws` is confirmed
text-JSON-frame-only). Full detail: [`PHASE_2_3_ROADMAP.md`](../PHASE_2_3_ROADMAP.md)
"Item 1 in detail" (lines 779-797).

**This plan deliberately jumps that queue.** Rationale: an interview timeline
forces it, not a reassessment of product priority. Concretely, this means:

- This build does **not** block or get blocked by Waves 2-5 — it's additive,
  isolated to a new WS route and new provider modules, and does not touch the
  live `WS /chat/ws` text handler.
- It does **not** retroactively promote Voice up the product roadmap. Once
  interview prep is done, whether/how this code graduates into an actual
  roadmap item is a separate decision.
- It intentionally narrows the roadmap's full scope (multi-surface,
  vendor-undecided, transport-undecided) down to one concrete, shippable
  slice: **Chat only, Deepgram + ElevenLabs, new dedicated WS route.**

## 3. Scope

**In scope:**
- Streaming STT (Deepgram) → existing `ChatService`/Generation Runtime →
  streaming TTS (ElevenLabs), over a new dedicated WebSocket.
- Visible live transcript in the existing chat UI.
- Barge-in / basic endpointing.
- Latency instrumentation via the existing Prometheus/Grafana setup.

**Out of scope (explicitly deferred, not forgotten):**
- Linear Research / Deep Research surfaces (roadmap itself recommends Chat
  first; Deep Research's async/multi-approval shape doesn't map onto live
  voice at all).
- Modifying the existing `WS /chat/ws` text handler.
- WhatsApp/email/phone (PSTN) telephony integration — JD lists these as
  separate channels; this POC only builds the voice engineering primitives,
  not channel delivery infrastructure.
- Multi-vendor fallback/failover between STT or TTS providers.
- Production hardening (auth on the new WS route beyond what Chat already
  requires, load testing, cost caps) — POC-grade only.

## 4. Vendor selection — why Deepgram + ElevenLabs, why not OpenAI

**Why voice needs a vendor at all, rather than building STT/TTS in-house:**
streaming speech recognition and speech synthesis are large trained models in
their own right (acoustic model + language model for STT, a vocoder for TTS);
building or self-hosting either to a real-time, production-acceptable
accuracy/latency bar is its own multi-month research effort, not a
POC-in-a-week task. Every option below is "buy," not "build" — the
engineering work is in the orchestration around them (transport, sentence
buffering, barge-in, guardrail reuse), not in the models themselves.

**Why two vendors (Deepgram for STT, ElevenLabs for TTS) instead of one
combined API — specifically, instead of OpenAI's Realtime API, which does
STT+LLM+TTS in a single WebSocket session:**

| Consideration | Deepgram + ElevenLabs (chosen) | OpenAI Realtime API (rejected for this POC) |
|---|---|---|
| Who does the reasoning | **Your own** `ChatService`/Generation Runtime — the transcript is just another input to the existing agent | OpenAI's model inside the Realtime session does the reasoning; your Generation Runtime is bypassed entirely for voice turns |
| RAG / retrieved context | Flows in exactly like typed chat, because the LLM call is still yours | Would require injecting retrieved context into the Realtime session's own context window via a separate mechanism — a second, divergent integration path |
| Guardrails | Existing `GuardrailService` runs on the transcript before generation, same as text | Realtime API generates and speaks in one loop; intercepting output before it's spoken for a guardrail check is a fundamentally harder mid-stream problem |
| Memory / context persistence | Existing memory read/write path, unchanged | Same integration problem as RAG above |
| Interview narrative | "I composed best-of-breed STT/TTS around my existing agent" — directly demonstrates the JD's dialogue-management/RAG/guardrails bullets | "I called one API that does everything" — demonstrates far less of the JD's actual list, since none of *your* orchestration is exercised |
| Latency / control | Two hops (STT then your LLM then TTS) — slightly more latency, but each stage is independently inspectable/tunable | One hop, likely lower raw latency, but a black box — can't independently reason about where time is spent |
| Cost | Two separate metered services, both with usable free tiers for a POC | Bundled per-minute pricing; harder to isolate voice cost from LLM cost |

**Bottom line:** OpenAI Realtime is the right choice if the goal is "ship a
voice assistant fast" with no existing agent to preserve. It is the *wrong*
choice here because the goal is specifically to demonstrate integrating voice
**around an existing production RAG/guardrails/memory stack** — which is what
this JD is actually asking about. Composing separate STT and TTS vendors is
what forces (and lets you talk about) that integration work.

**Why Deepgram specifically (STT):** streaming-first API designed for exactly
this "continuous partial transcription" shape (not a batch/record-then-send
model retrofitted for streaming), a mature Python SDK, built-in
endpointing/VAD signals that T10-T11's barge-in logic depends on directly,
and a free tier large enough to cover a week of development.

**Why ElevenLabs specifically (TTS):** streaming websocket API that accepts
text incrementally (sentence-by-sentence, matching T7's buffering approach)
rather than requiring a complete string up front, low time-to-first-audio,
and it's currently the most commonly cited TTS vendor in real-world
streaming-voice-agent stacks — reduces the risk of hitting undocumented
integration surprises the JD's "production-grade" bar would care about.

**Alternatives considered and not chosen:** Azure Speech and Google
Cloud Speech-to-Text/Text-to-Speech are viable STT/TTS alternatives with
similar streaming support, but neither adds anything to the interview
narrative over Deepgram/ElevenLabs and both require heavier cloud-account
setup (full Azure/GCP project provisioning) than a two-minute API-key
signup — not worth the extra setup time for a one-week POC.

## 5. Architecture

```
 Browser mic ──(PCM/Opus audio frames)──▶  WS /chat/voice  ──▶ Deepgram streaming STT
                                                                     │
                                                          interim + final transcript
                                                                     │
                                                                     ▼
                                                     existing ChatService.generate()
                                                     (same guardrail checks, same
                                                      Generation Runtime as typed chat)
                                                                     │
                                                        streamed response tokens
                                                                     │
                                                                     ▼
                                                sentence-boundary buffer ─▶ ElevenLabs
                                                                streaming TTS
                                                                     │
 Browser audio playback ◀──(audio frames)── WS /chat/voice ◀────────┘
```

Key decision: the transcript enters the **same** `ChatService` call path a
typed message would, so guardrails, memory/context persistence, and RAG
retrieval are all inherited for free rather than re-implemented for voice.

## 6. Environment & configuration

| Variable | Purpose | Where read |
|---|---|---|
| `DEEPGRAM_API_KEY` | Streaming STT auth | new field in [`apps/api/app/core/settings.py`](../../apps/api/app/core/settings.py), alongside existing provider keys |
| `ELEVENLABS_API_KEY` | Streaming TTS auth | same file |
| `VOICE_ENABLED` | Feature flag, default `false` | same file — lets this ship dark until deliberately enabled |

Setup steps (manual, one-time): create free-tier accounts at deepgram.com and
elevenlabs.io, generate API keys, add to local `.env`. No key values are ever
pasted into this repo or into chat with the assistant.

## 7. Task breakdown

Each task has an ID used in the traceability matrix (§9). Status checkboxes
are meant to be updated in place as work progresses. **No task in this
section starts until the branch-workflow step in §10 has happened** — see
that section before beginning T1.

### Day 1-2 — STT spike (standalone from Chat)
- [ ] **T1** Add `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`, `VOICE_ENABLED` to
      `app/core/settings.py`.
- [ ] **T2** New package `app/ai/runtime/voice/stt/deepgram.py`, mirroring the
      existing provider shape in
      [`app/ai/runtime/generation/providers/base.py`](../../apps/api/app/ai/runtime/generation/providers/base.py):
      a thin async wrapper opening Deepgram's streaming websocket, yielding
      interim + final transcript events.
- [ ] **T3** New route `WS /chat/voice` in
      [`app/api/v1/chat.py`](../../apps/api/app/api/v1/chat.py) (separate from
      the existing `WS /chat/ws` at line 911) that accepts binary audio
      frames, pipes them to T2, and echoes transcript events back as JSON —
      no chat integration yet, just prove the STT loop works end-to-end.
- [ ] **T4** Minimal static test page (mic capture via `MediaRecorder`,
      renders interim/final transcript text) to validate T3 without touching
      the real frontend yet.

### Day 3 — Wire into real Chat
- [ ] **T5** On final transcript, call the existing `ChatService` generation
      path exactly as a typed message would (same request shape, same
      guardrail checks, same memory/RAG context building).
- [ ] **T6** Confirm via logs/tracing that a voice-originated turn produces
      the same `GenerationRequest`/artifact/observability trail as a
      typed-message turn (this is the check that voice is a new *input*, not
      a parallel, divergent code path).

### Day 4-5 — Streaming TTS
- [ ] **T7** New package `app/ai/runtime/voice/tts/elevenlabs.py`: consumes a
      text stream, buffers to sentence boundaries, opens ElevenLabs' streaming
      websocket, yields audio chunks.
- [ ] **T8** Wire the Generation Runtime's existing token stream (already
      real today for typed chat — `app/ai/runtime/generation`'s streaming
      path) into T7's sentence buffer.
- [ ] **T9** Stream T7's audio chunks back over `WS /chat/voice`; extend T4's
      test page to play them via the Web Audio API.

### Day 6 — Barge-in / endpointing
- [ ] **T10** Detect user speech restart while TTS playback is in-flight
      (Deepgram interim-result signal) and emit a "stop audio" event to the
      client; client halts playback immediately.
- [ ] **T11** Basic silence-based endpointing tuning (avoid cutting off
      transcription mid-sentence vs. waiting too long before responding) —
      this is the detail worth being able to explain in the interview.

### Day 7 — Instrumentation & real chat UI integration
- [ ] **T12** Emit latency metrics — time-to-first-interim-transcript,
      time-to-first-audio-byte, end-to-end turn latency — through the
      existing Prometheus setup
      (`app/ai/observability/prometheus/`), following the pattern already
      used for Generation Runtime latency.
- [ ] **T13** Replace T4's throwaway test page with a real toggle inside the
      existing chat UI (mic button, live transcript rendered through the
      existing message-rendering component, audio playback indicator).
- [ ] **T14** End-to-end manual test pass: multi-turn voice conversation,
      barge-in, a guardrail-triggering phrase (confirm existing guardrails
      fire on voice input same as text), and a RAG-requiring question
      (confirm retrieval context reaches the response same as typed chat).

## 9. Requirements traceability matrix

Maps each relevant JD bullet to the concrete task(s) that demonstrate it, the
files touched, and how it's verified — so each interview claim ("I built X")
has a specific artifact behind it.

| Req ID | JD requirement | Task(s) | Primary files | Verification | Status |
|---|---|---|---|---|---|
| REQ-1 | Multi-channel delivery incl. voice | T1-T3, T9, T13 | `chat.py`, `voice/stt/`, `voice/tts/` | Manual: voice round-trip works in browser | Not started |
| REQ-2 | Multi-turn dialogue management / conversational systems | T5, T6, T14 | `ChatService` call site in T5 | Multi-turn manual conversation retains context | Not started |
| REQ-3 | Context persistence / memory strategies | T5, T6 | reuses existing memory read/write path (no new code) | Trace shows same memory calls as typed chat | Not started |
| REQ-4 | RAG / enterprise knowledge integration | T5, T14 | reuses existing retrieval path (no new code) | T14's RAG-requiring question test | Not started |
| REQ-5 | Guardrails, fallback, failure handling | T5, T14 | reuses existing `GuardrailService` (no new code) | T14's guardrail-triggering phrase test | Not started |
| REQ-6 | AI safety (prompt injection, output validation) | T5 | same guardrail reuse as REQ-5 | Same as REQ-5 | Not started |
| REQ-7 | Async processing / event-driven architecture | T3, T7-T9 | `chat.py` WS route, both provider modules | Code review: all I/O is async, no blocking calls in the WS handler | Not started |
| REQ-8 | Latency, cost (token usage), response quality optimization | T8, T10-T12 | sentence-buffer logic, T12 metrics | T12's three latency metrics have real recorded values | Not started |
| REQ-9 | Monitoring, logging, observability | T12 | `app/ai/observability/prometheus/` | Metrics visible in Grafana | Not started |
| REQ-10 | Evaluation approaches (testing, benchmarking) | T14 | manual test script (this doc §6) | T14 checklist fully executed | Not started |
| REQ-11 | Production-grade reliability standards | T10, T11, `VOICE_ENABLED` flag (T1) | barge-in logic, feature flag | Flag defaults off; barge-in tested under T14 | Not started |

**Explicitly not claimed by this POC** (be honest about this in the
interview rather than overstating): Kubernetes/Docker deployment of the voice
path specifically, HITL approval workflows (voice here doesn't route through
an `interrupt()` checkpoint), multi-channel telephony/WhatsApp delivery, load
testing, multi-vendor STT/TTS failover.

## 10. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Deepgram/ElevenLabs streaming SDK has integration friction not visible from docs | Med | Timebox T2/T7 spikes to half a day each before committing to the rest of the week's plan; both vendors have Python SDK examples for exactly this streaming shape |
| ElevenLabs free-tier character quota runs out mid-week during testing | Med | Keep TTS test utterances short during T7-T9 development; save quota for the T14 full run-through |
| Barge-in (T10-T11) is genuinely fiddly and eats more than one day | High | It's explicitly the "if time allows" polish item — T1-T9 alone already cover REQ-1 through REQ-9 in the matrix above; T10-T11 only add REQ-11 polish |
| New `WS /chat/voice` route accidentally shares state with `WS /chat/ws` and destabilizes existing text chat | Low | Route is a fully separate handler function; `VOICE_ENABLED` flag keeps it inert if disabled |

## 11. Non-breaking guarantees & branch workflow

**Non-negotiable constraint for this build: existing Chat, Linear Research,
and Deep Research behavior must be unaffected, whether `VOICE_ENABLED` is on
or off.** How each task class enforces that:

| Change type | Tasks | Why it can't break existing behavior |
|---|---|---|
| New settings fields (`DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`, `VOICE_ENABLED`) | T1 | Purely additive fields on the settings model; nothing existing reads them, so nothing existing can be affected by their presence, absence, or value |
| New provider packages (`app/ai/runtime/voice/stt/`, `.../tts/`) | T2, T7 | New files in a new subpackage; zero existing imports point at this code, so it is unreachable dead code until something explicitly calls it |
| New WS route (`WS /chat/voice`) | T3, T9, T10 | A separate route handler function, registered on the router alongside (not replacing) `WS /chat/ws`. FastAPI dispatches by path, so the existing text route's code path is never entered by voice traffic and vice versa |
| Calling `ChatService`/Generation Runtime from the voice path | T5, T6, T8 | These are **calls into** existing, unmodified functions — the same call a typed message already makes. No existing function signature, behavior, or call site is changed. If this integration is wrong, it fails inside the new voice path only; it cannot corrupt a typed-chat request, since typed chat doesn't go through any of this new code |
| Frontend changes | T4 (throwaway test page, not part of the real app), T13 (mic button + playback indicator added to existing chat UI) | T13 is the only task touching real frontend code, and it is additive UI (a new button/indicator), not a modification of existing message-send/render logic. Should be reviewed as a diff before merging to confirm no existing component props/behavior changed |
| Observability | T12 | New metrics only; does not alter existing Generation Runtime or Chat metrics |

**Verification that nothing broke, before this is considered mergeable:**
run the existing repo-root `tests/` pytest suite and confirm it's green with
no regressions, in addition to T14's manual voice-specific pass. If any
existing test fails after this work, treat it as a blocking regression, not
something to work around.

**Branch workflow:** none of the tasks in §7 start on the current branch.
Before T1, cut a new branch from the current branch tip (e.g.
`git checkout -b voice-poc`) dedicated to this work. Rationale: this keeps
the diff isolated and reviewable, makes it trivial to discard the whole POC
if the interview timeline changes, and means the non-breaking guarantees
above can be checked with a single clean diff against the current branch
rather than disentangled from other in-flight work. Nothing in this plan
should be implemented until that branch exists.

## 12. Definition of done for interview readiness

Minimum bar (covers REQ-1 through REQ-9): T1-T9 complete, T14's manual test
pass executed at least once successfully end-to-end, three latency numbers
from T12 recorded and memorized for interview discussion.

Stretch bar (adds REQ-11 polish): T10-T13 also complete.
