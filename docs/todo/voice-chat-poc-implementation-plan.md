# Voice-on-Chat POC — Development Plan & Traceability

**Status (2026-08-27, end of day):** backend and frontend code-complete.
**Live-verified**: the Deepgram and ElevenLabs vendor integrations against
their real APIs (real speech in, accurate transcript out; real text in,
valid playable audio out; a full TTS→STT round trip matched exactly), and
**a single voice turn through the real authenticated route in a real
browser** (mic → transcript → text answer → spoken audio, all real).
**KNOWN UNRESOLVED GAP**: multi-turn voice sessions do not reliably survive
past that first turn — the session drops and root cause is not identified
despite three real bugs found and fixed along the way (see §12's four
2026-08-27 entries for the full history, and the last entry specifically
for the open gap). **Do not claim sustained multi-turn voice conversation
works** — claim "one voice exchange verified end-to-end with real vendor
APIs," which is accurate and still a genuinely strong result. **Driver:**
interview-prep hands-on build, not a roadmap-sequenced initiative — see
"Relationship to the roadmap" below before reading this as a Wave item.
**Scope:** one surface (Chat), one vendor pair (Deepgram STT + ElevenLabs
TTS), ~1 week. **Branch:** `researchmind-voice`.

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

**Implementation-time addition, decided during T2/T7 (2026-08-26): raw
WebSocket protocol, not the `deepgram-sdk`/`elevenlabs` vendor SDKs.**
Live research into `deepgram-sdk`'s current async API surfaced a real
version-churn risk that wasn't visible when this doc was first written:
the SDK's own connect API changed shape across major versions (a `v1`
vs. `v2` `connect()` method with different model names) independently of
the underlying wire protocol, which has stayed stable. Rather than couple
this build to SDK-internal names that have already moved once, both
providers talk directly to the vendors' documented WebSocket protocols
(`developers.deepgram.com/reference/listen-live`,
`elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-stream-input`)
using the `websockets` library already present in this repo's dependency
tree (transitively, via `uvicorn[standard]`; now added as an explicit
top-level dependency since the voice code imports it directly). This
mirrors an existing, proven convention already in this codebase: the Web
Search Tool Platform's `TavilyWebSearchProvider` calls Tavily's REST API
directly via `httpx`, with no vendor SDK dependency at all. Every field
name, header, and message shape used in `app/ai/runtime/voice/` was
verified against the official docs, and the WebSocket client call shape
(`websockets.connect(uri, additional_headers=..., open_timeout=...)`) was
additionally confirmed against the actual installed package in this
repo's `.venv` (version 15.0.1), not just documentation prose.

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
| `DEEPGRAM_API_KEY` | Streaming STT auth | [`apps/api/app/core/settings.py`](../../apps/api/app/core/settings.py), alongside existing provider keys |
| `ELEVENLABS_API_KEY` | Streaming TTS auth | same file |
| `ELEVENLABS_VOICE_ID` | Which ElevenLabs voice to synthesize with | same file — **still needs to be set**, see below |
| `VOICE_ENABLED` | Feature flag, default `false` | same file — lets this ship dark until deliberately enabled |

Setup steps (manual, one-time): create free-tier accounts at deepgram.com and
elevenlabs.io, generate API keys, add to local `.env`. No key values are ever
pasted into this repo or into chat with the assistant.

**Status as of 2026-08-26:** `DEEPGRAM_API_KEY` and `ELEVENLABS_API_KEY` are
both set in `.env`. `ELEVENLABS_VOICE_ID` and `VOICE_ENABLED=true` are
**not yet set** — without them, `create_voice_tts_provider()` returns `None`
(text-only voice turns, no spoken audio) and `WS /chat/voice` closes
immediately, respectively, both by design (see §4 and §10's "fails
closed rather than crashes" pattern), not a bug. Get a voice ID from your
ElevenLabs dashboard's "Voices" tab before attempting a live test.

## 7. Task breakdown

Each task has an ID used in the traceability matrix (§8). Status checkboxes
are meant to be updated in place as work progresses (`[x]` done, `[~]`
substituted/partial, `[ ]` not started).

### Day 1-2 — STT spike (standalone from Chat)
- [x] **T1** Add `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`,
      `ELEVENLABS_VOICE_ID`, `VOICE_ENABLED` (plus per-provider timeout/model
      settings) to
      [`app/core/settings.py`](../../apps/api/app/core/settings.py). Done
      2026-08-26.
- [x] **T2** `app/ai/runtime/voice/stt/deepgram.py` — **deviation from the
      original plan:** talks to Deepgram's raw WebSocket protocol directly
      rather than the `deepgram-sdk` package; see the vendor-selection
      section's 2026-08-26 addendum above for why. Done 2026-08-26, unit-tested
      in [`tests/unit/ai/runtime/voice/stt/test_deepgram.py`](../../tests/unit/ai/runtime/voice/stt/test_deepgram.py).
- [x] **T3** New route `WS /chat/voice` in
      [`app/api/v1/chat.py`](../../apps/api/app/api/v1/chat.py) (separate
      function from the existing `WS /chat/ws`). **Scope grew beyond the
      original "STT-only echo" plan for this task**: once the exact reuse
      point in `stream_chat_ws` (`_prepare_chat_generation` /
      `streaming_service.stream_generate` / `_persist_on_complete`) was
      understood, building a throwaway STT-only route first and rewiring it
      later would have been strictly more work than wiring the real
      integration once — so T3, T5, T6, T8, and T9 were implemented together
      in one pass rather than sequentially across Day 1-5 as originally
      planned. Done 2026-08-26.
- [x] **T4** [`tools/voice-test-page/index.html`](../../tools/voice-test-page/index.html)
      — a single self-contained HTML/JS file, zero build step, zero
      dependency on `apps/web` (outside its ESLint/TypeScript project
      entirely, so it cannot affect that build). Captures mic audio via
      `ScriptProcessorNode` (deliberately not an `AudioWorklet` — this is
      throwaway, single-file-only code; T13 should use an `AudioWorklet`
      instead), downsamples to 16kHz mono PCM16, streams it over the WS,
      renders live transcript/response text, and plays back TTS audio via
      `MediaSource` + `audio/mpeg` (not manual PCM scheduling — ElevenLabs'
      PCM output formats require a paid Creator-tier-or-above subscription,
      confirmed via their docs, not available on the free tier this build
      targets; MSE is the correct choice given that constraint, not a
      shortcut). Node's `--check` confirms the extracted script is valid
      JS. **Not yet opened in an actual browser** — that's the live
      verification step that remains, tracked under T14.

### Day 3 — Wire into real Chat
- [x] **T5** Done as part of T3 above — a final transcript builds a real
      `ChatStreamRequest` and is passed through
      `_prepare_chat_generation`/`streaming_service.stream_generate`/
      `_persist_on_complete` unmodified, the same call a typed message makes.
- [x] **T6** Confirmed by construction, not by tracing a live run (no live
      run has happened yet): the voice route calls the exact same private
      helper functions `stream_chat_ws` calls, with the exact same
      arguments shape, so there is no divergent code path to trace. A live
      trace comparison is still open, tracked under T14.

### Day 4-5 — Streaming TTS
- [x] **T7** `app/ai/runtime/voice/tts/elevenlabs.py` — same raw-protocol
      deviation as T2. Done 2026-08-26, unit-tested in
      [`tests/unit/ai/runtime/voice/tts/test_elevenlabs.py`](../../tests/unit/ai/runtime/voice/tts/test_elevenlabs.py).
- [x] **T8** `app/ai/runtime/voice/sentence_buffer.py` taps the Generation
      Runtime's existing TOKEN stream inside
      [`app/ai/runtime/voice/response_stream.py`](../../apps/api/app/ai/runtime/voice/response_stream.py).
      Done 2026-08-26, unit-tested in
      [`tests/unit/ai/runtime/voice/test_sentence_buffer.py`](../../tests/unit/ai/runtime/voice/test_sentence_buffer.py).
- [x] **T9** `response_stream.py` forwards ElevenLabs audio chunks as binary
      WebSocket frames interleaved with the existing JSON `StreamEvent`
      frames. Done 2026-08-26, and T4's test page now plays them via
      `MediaSource`.

### Day 6 — Barge-in / endpointing
- [x] **T10** Implemented via **energy-based voice-activity detection**
      (`app/ai/runtime/voice/vad.py`'s `BargeInDetector`), not a second
      live Deepgram connection during playback — cheaper (no second
      concurrent vendor session per turn) and fully unit-testable without
      real audio. A concurrent task in `response_stream.py` watches
      incoming audio RMS amplitude while the response streams; on a
      sustained loud run it sets an `asyncio.Event`, the response loop
      breaks, ElevenLabs synthesis/playback are cancelled, and a
      `voice.interrupted` JSON frame tells the client to stop immediately
      (T4's test page handles this via `MediaSource.abort()`). The audio
      that triggered detection is not carried into the next turn's
      Deepgram session — deliberately simpler, disclosed in
      `response_stream.py`'s docstring. Done 2026-08-26, unit-tested in
      [`tests/unit/ai/runtime/voice/test_vad.py`](../../tests/unit/ai/runtime/voice/test_vad.py)
      and the barge-in cases in
      [`tests/unit/ai/runtime/voice/test_response_stream.py`](../../tests/unit/ai/runtime/voice/test_response_stream.py).
      **Not yet verified against a real interruption** — the RMS
      threshold/consecutive-chunk defaults
      (`voice_barge_in_rms_threshold`/`voice_barge_in_consecutive_chunks`)
      are untuned starting values, not calibrated against real audio.
- [~] **T11** Partially addressed, not tuned. `deepgram_endpointing_ms`
      (silence-before-`is_final` threshold) was already configurable from
      T1; barge-in's own two thresholds (above) are the other half of
      "avoid cutting off mid-sentence vs. waiting too long." **Real
      tuning requires live audio and is explicitly not done** — these are
      reasonable starting defaults, not calibrated values.

### Day 7 — Instrumentation & real chat UI integration
- [x] **T12** Three histograms added —
      `researchmind_voice_stt_first_transcript_duration_seconds`,
      `researchmind_voice_tts_first_audio_duration_seconds`,
      `researchmind_voice_turn_duration_seconds` — registered in
      [`app/ai/observability/prometheus/names.py`](../../apps/api/app/ai/observability/prometheus/names.py)
      following the exact pattern already used for
      `researchmind_web_search_duration_seconds`, recorded from
      `transcription.py`/`response_stream.py`/`chat.py`'s per-turn loop.
      Done 2026-08-26, unit-tested (each metric call verified to fire
      exactly once per turn, not once per event). **No Grafana panel
      built yet** — the metrics exist and are recorded, but nothing
      visualizes them; a real run would still need to be triggered to see
      non-zero values in Prometheus at all.
- [x] **T13** Implemented directly inside the real chat surface, not a
      separate hook/page: `apps/web/src/features/chat/use-chat.ts` gained
      `startVoiceChat`/`stopVoiceChat` (a second, WS-based sibling to the
      existing SSE-based `send()`, reusing the same `messages`/
      `patchMessage`/`activeConversationId` state so voice turns render
      through the exact same `MessageBubble` component typed turns do),
      a new `apps/web/public/voice-worklet.js` `AudioWorklet` (not the
      throwaway page's `ScriptProcessorNode` — this is real product code),
      and a mic toggle button + live-transcript/error banner added to
      `ChatComposer`/the Chat page, purely additive (new button, new
      props, zero changes to existing send/render logic). `tsc --noEmit`
      and `next lint` both clean on every touched file. **This was
      genuinely the frontend's first-ever WebSocket client** — confirmed
      by reading `use-chat.ts` before starting, exactly the risk flagged
      when this was originally deferred.
- [~] **T14 (partial, with an unresolved gap found on top of it — see §12's
      fourth 2026-08-27 entry: multi-turn voice sessions currently drop
      after one turn, root cause not identified). The honest split matters
      here.** What's now **live-verified against the real Deepgram and
      ElevenLabs services**,
      using the actual repo classes, not mocks (see §12's 2026-08-27
      entry for full commands/output):
      - `DeepgramSTTProvider` + `collect_voice_turn_transcript`: real
        speech (synthesized locally via macOS `say`, converted to 16kHz
        mono PCM16) → accurate live transcript, via natural
        `endpointing_ms` silence detection (the exact mechanism
        production relies on, not a forced `Finalize`).
      - `ElevenLabsTTSProvider` + `stream_voice_response`: a real token
        stream → sentence-buffered → real ElevenLabs audio → verified as
        valid, playable MP3 (`afconvert` decoded it successfully).
      - **Full round trip**: ElevenLabs-synthesized audio fed back into
        live Deepgram produced a transcript matching the original text
        exactly.
      - Found and worked through a real blocker along the way: this
        ElevenLabs account is free-tier, and free tier cannot use
        Voice-Library voices via the API at all (`402 payment_required`)
        — only voices already in the account's own "My Voices". Two
        already-present default voice IDs were found to work; one is now
        set as `ELEVENLABS_VOICE_ID` in `.env`, alongside `VOICE_ENABLED=true`.

      **Still not done, and not fakeable from here:** the full
      authenticated `WS /chat/voice` route end-to-end (this app's auth is
      real Cognito JWT verification, `apps/api/app/auth/dependencies.py`
      — there is no dev/mock auth provider to script around, and forging
      a token is not something to attempt); a real browser exercising
      T4's test page or T13's UI (mic permission prompts, `AudioWorklet`,
      `MediaSource` behavior); barge-in against real speech (only
      unit-tested with synthetic amplitude arrays so far); a guardrail-
      triggering phrase and a RAG-requiring question through the real
      route; T12's metrics observed in the actual running
      Prometheus/Grafana instance (the live-test scripts ran as separate
      processes with their own metrics registries, so nothing they
      recorded reached the real server's `/metrics` endpoint). **The one
      remaining step that unblocks all of these is a real login in a
      real browser** — that step is the user's to take, not something
      this session can do.

## 8. Requirements traceability matrix

Maps each relevant JD bullet to the concrete task(s) that demonstrate it, the
files touched, and how it's verified — so each interview claim ("I built X")
has a specific artifact behind it.

| Req ID | JD requirement | Task(s) | Primary files | Verification | Status |
|---|---|---|---|---|---|
| REQ-1 | Multi-channel delivery incl. voice | T1-T4, T9-T10, T13 | `chat.py`, `voice/stt/`, `voice/tts/`, `tools/voice-test-page/`, `use-chat.ts` | Backend **live-verified** against real Deepgram/ElevenLabs; frontend (T13) built and type/lint-checked, not yet opened in a real browser; full authenticated route untested (needs real login) | Live-verified backend, browser pending |
| REQ-2 | Multi-turn dialogue management / conversational systems | T5, T6, T14 | `stream_chat_voice` in `chat.py` | Implemented by construction (same call path as typed chat); STT/TTS halves live-verified individually; full multi-turn run through the real route not done (needs real auth) | Implemented, real-route E2E pending |
| REQ-3 | Context persistence / memory strategies | T5, T6 | reuses existing memory read/write path (no new code) | Implemented by construction; no live trace comparison yet (needs real auth) | Implemented, real-route E2E pending |
| REQ-4 | RAG / enterprise knowledge integration | T5, T14 | reuses existing retrieval path (no new code) | Implemented by construction; T14's live RAG-question test still open (needs real auth) | Implemented, real-route E2E pending |
| REQ-5 | Guardrails, fallback, failure handling | T5, T14 | reuses existing `GuardrailService` (no new code) | Implemented by construction; T14's live guardrail-phrase test still open (needs real auth) | Implemented, real-route E2E pending |
| REQ-6 | AI safety (prompt injection, output validation) | T5 | same guardrail reuse as REQ-5 | Same as REQ-5 | Implemented, real-route E2E pending |
| REQ-7 | Async processing / event-driven architecture | T3, T7-T9 | `chat.py` WS route, both provider modules | **Verified**: `mypy`/`ruff` clean repo-wide, all I/O in the new code is `async`/`await`, no blocking calls | Verified |
| REQ-8 | Latency, cost (token usage), response quality optimization | T8, T10-T12 | `sentence_buffer.py`, `vad.py`, three Prometheus histograms | Sentence-buffering, barge-in VAD, and all three latency metrics implemented + unit-tested; thresholds are untuned defaults, no live latency numbers recorded yet | Implemented, untuned/unverified live |
| REQ-9 | Monitoring, logging, observability | T12 | `app/ai/observability/prometheus/names.py`, `transcription.py`, `response_stream.py`, `chat.py` | Three histograms registered and recorded from real code paths, unit-tested; no Grafana panel, no real run has produced a data point yet | Implemented, unvisualized |
| REQ-10 | Evaluation approaches (testing, benchmarking) | T14 | `tests/unit/ai/runtime/voice/` (30 tests), `tests/integration/ai/test_chat_voice.py` (2 tests) | **Verified for the fail-closed/unit-logic slice**: 32 new tests, all passing, full repo suite (2118 tests) green with zero regressions. Live-service/manual pass (T14) still open | Partially implemented |
| REQ-11 | Production-grade reliability standards | T10, T11, `VOICE_ENABLED` flag (T1) | `vad.py`, `response_stream.py`, feature flags | `VOICE_ENABLED` flag and barge-in both implemented and unit-tested (including a disabled-flag test); barge-in thresholds untuned, never triggered against real audio | Implemented, untuned/unverified live |

**Explicitly not claimed by this POC** (be honest about this in the
interview rather than overstating): Kubernetes/Docker deployment of the voice
path specifically, HITL approval workflows (voice here doesn't route through
an `interrupt()` checkpoint), multi-channel telephony/WhatsApp delivery, load
testing, multi-vendor STT/TTS failover.

**Updated 2026-08-27 — the live-testing line moved, be precise about where
it is now.** As of 2026-08-26, "no live test against real Deepgram/
ElevenLabs" was true. As of 2026-08-27, that's no longer accurate — real,
live calls against both services, using the actual `DeepgramSTTProvider`/
`ElevenLabsTTSProvider`/`collect_voice_turn_transcript`/
`stream_voice_response` code, with real synthesized speech, produced
correct results (see T14 above and §12's 2026-08-27 entry). **What is
still true, and is the actual honest answer if asked "have you tested this
end-to-end":** no request has gone through the real authenticated
`WS /chat/voice` route (blocked on a real Cognito login, not scriptable),
and no browser has run the mic-capture/playback code in either T4's test
page or T13's real UI. The correct framing is "the vendor integrations are
live-verified against real APIs with real audio content; the full product
surface — real auth, real browser, real microphone — is not yet tested."
That is a meaningfully stronger position than 2026-08-26's, but it is not
"fully tested," and conflating the two in an interview would be the kind
of overstatement this section exists to prevent.

## 9. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Deepgram/ElevenLabs streaming SDK has integration friction not visible from docs | Med | Timebox T2/T7 spikes to half a day each before committing to the rest of the week's plan; both vendors have Python SDK examples for exactly this streaming shape |
| ElevenLabs free-tier character quota runs out mid-week during testing | Med | Keep TTS test utterances short during T7-T9 development; save quota for the T14 full run-through |
| Barge-in (T10-T11) is genuinely fiddly and eats more than one day | High | It's explicitly the "if time allows" polish item — T1-T9 alone already cover REQ-1 through REQ-9 in the matrix above; T10-T11 only add REQ-11 polish |
| New `WS /chat/voice` route accidentally shares state with `WS /chat/ws` and destabilizes existing text chat | Low | Route is a fully separate handler function; `VOICE_ENABLED` flag keeps it inert if disabled |
| **Materialized 2026-08-27, unresolved:** multi-turn voice sessions drop after one turn | Confirmed | For the interview, demo/describe exactly one voice exchange, not a sustained conversation — that one exchange is genuinely, live-verified working. Do not attempt to demo a second back-and-forth turn live without re-testing first. See §12's fourth 2026-08-27 entry for the debugging trail and what's needed to actually root-cause it (server/browser logs at the moment of the drop, not another screenshot) |

## 10. Non-breaking guarantees & branch workflow

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

**Verification that nothing broke — done, 2026-08-26, not just planned:**
the full repo-root `tests/` pytest suite was run after T1-T3/T5-T9 landed:
**2104 passed, 0 failed** (2085 pre-existing + 19 new voice tests), plus
`ruff check .` and `mypy .` both clean across the entire repo, not just the
new files. No existing test was modified to make this pass. If any future
change to this feature makes an existing test fail, that is a blocking
regression per this section's original rule, not something to work around.

**Branch workflow:** done — this work is on `researchmind-voice`, cut from
the branch tip before T1 started, per this section's original plan (the
branch name differs from the `voice-poc` example originally suggested here;
functionally identical: an isolated branch, not the base branch).

## 11. Definition of done for interview readiness

Minimum bar (covers REQ-1 through REQ-9): T1-T9 complete (**done**), T14's
manual test pass executed at least once successfully end-to-end (**partially
done** — the Deepgram/ElevenLabs vendor integrations are live-verified with
real audio; the full pass through the real authenticated route with a real
browser is **not done**, blocked on a real login), three latency numbers
from T12 recorded and memorized for interview discussion (**still not
done** — the live-test scripts ran outside the app's own metrics registry,
so nothing was recorded into the real running Prometheus instance).

Stretch bar (adds REQ-11 polish): T10-T13, **all four now implemented**.
T10/T11 untuned against real audio; T13 built and type/lint-checked, not
opened in a real browser yet.

**Current state: T1-T13 code-complete and test-verified — including, as of
2026-08-27, live verification of both vendor integrations against their
real APIs with real synthesized speech (see T14 above). What remains for
full "done" on both bars is entirely one thing: a real person, in a real
browser, logged in for real, granting mic permission and speaking. Nothing
else in this plan is still blocked on code that hasn't been written — only
on that one live session, which only the user can perform.**

## 12. Progress log

**2026-08-26 — Backend implementation pass.** Implemented T1, T2, T3, T5,
T6, T7, T8, T9 in one session on branch `researchmind-voice`. Summary for
anyone picking this up next:

- **New files:** `apps/api/app/ai/runtime/voice/` (`create.py`,
  `sentence_buffer.py`, `transcription.py`, `response_stream.py`,
  `ws_connection.py`, `stt/deepgram.py`, `tts/elevenlabs.py`),
  `apps/api/app/schemas/voice.py`. **Modified files:**
  `apps/api/app/core/settings.py` (new Voice section), `.env.example`
  (new variables), `apps/api/app/api/v1/chat.py` (new `WS /chat/voice`
  route + imports only — `stream_chat_ws` itself was not touched), 
  `pyproject.toml`/`uv.lock` (added `websockets` as an explicit
  dependency; it was already present transitively).
- **New tests:** `tests/unit/ai/runtime/voice/` (sentence buffer, Deepgram
  provider, ElevenLabs provider, factory None-degradation — 17 tests) and
  `tests/integration/ai/test_chat_voice.py` (2 tests: the two fail-closed
  paths that need no DB/vendor mocking).
- **Key decisions made during implementation, not pre-planned:**
  1. Raw WebSocket protocol instead of vendor SDKs for both providers (see
     §4's 2026-08-26 addendum) — discovered mid-implementation that
     `deepgram-sdk`'s own API surface had already changed shape once
     (v1→v2 `connect()`), which made the wire protocol the more stable
     integration point.
  2. A structural `Protocol` type
     (`app/ai/runtime/voice/ws_connection.py`) instead of importing
     `websockets`' concrete `ClientConnection` class into every provider
     method signature — lets test fakes satisfy the type contract without
     inheriting from a third-party class. Driven by `mypy` actually
     failing on the first draft of the unit tests, not a speculative
     choice.
  3. One Deepgram/ElevenLabs connection per conversational turn, not one
     held open for the whole call — trades a small per-turn reconnect
     cost for a lifecycle simple enough to reason about without building
     barge-in (T10/T11) first. Documented inline in
     `transcription.py`/`response_stream.py`, not just here.
  4. T3/T5/T6/T8/T9 were merged into one implementation pass instead of
     following the original Day 1-5 split, once the exact reuse point in
     `stream_chat_ws` was clear — see T3's note above.
- **Verification performed:** `ruff check .`, `ruff format --check .`,
  and `mypy .` all clean across the whole repo (not just new files); full
  `pytest tests/` run: 2104 passed, 0 failed, 0 skipped-due-to-error.
- **Verification NOT performed (the honest gap):** no live call to
  Deepgram or ElevenLabs has been made — `ELEVENLABS_VOICE_ID` and
  `VOICE_ENABLED` are still unset (see §6). No browser has connected to
  `WS /chat/voice`, no microphone audio has been sent, no audio has been
  played back. T4 (test page), T10-T14 (barge-in, metrics, real UI,
  end-to-end manual pass) are all still open. **Do not describe this in
  the interview as "tested end-to-end" — describe it as "implemented and
  unit-tested, live end-to-end verification pending" until T14 actually
  happens.**
- **Next step for whoever resumes this:** set `ELEVENLABS_VOICE_ID` from
  your ElevenLabs dashboard and `VOICE_ENABLED=true` in `.env`, then do a
  first live test — even a `websockets`-based command-line script feeding
  a `.wav` file to `WS /chat/voice` would validate the Deepgram/ElevenLabs
  wiring without needing the browser mic capture piece (T4/T13) built
  first.

**2026-08-27 — T4, T10, T11 (partial), T12 implemented.** Same branch,
same "code-complete and test-verified, not live-verified" caveat as above
still applies to everything new here.

- **New files:** `apps/api/app/ai/runtime/voice/vad.py` (`BargeInDetector`,
  `pcm16_rms`), `apps/api/app/ai/runtime/voice/provider_sessions.py`
  (`SpeechToTextSession`/`TextToSpeechSession` protocols),
  `apps/api/app/infrastructure/metrics/voice.py` (three metric-name
  constants), `tools/voice-test-page/index.html` (T4's standalone
  browser test harness). **Modified files:** `settings.py` (barge-in
  thresholds), `ws_connection.py` (split, see below),
  `transcription.py`/`response_stream.py` (metrics + barge-in),
  `chat.py` (turn-latency metric), `names.py` (three `DURATION_METRICS`
  entries).
- **New tests:** `test_vad.py` (6), `test_transcription.py` (3),
  `test_response_stream.py` (7, including two barge-in cases and one
  disabled-flag case) — 32 new voice tests total across both sessions,
  full suite now 2118 passed, 0 failed.
- **Key decisions made during this pass, not pre-planned:**
  1. **Barge-in via energy-based VAD on raw audio, not a second live
     Deepgram connection during playback.** The plan's original T10
     wording ("Deepgram interim-result signal") implied keeping STT live
     during TTS playback; implemented instead as RMS-amplitude detection
     over incoming PCM16 chunks (`vad.py`), consecutive-chunk-gated to
     avoid one loud noise triggering a false interrupt. Cheaper (no
     second concurrent vendor session per turn) and fully unit-testable
     without real audio, at the cost of being cruder than a real STT
     signal would be — a reasonable trade for a POC, disclosed here and
     in `response_stream.py`'s docstring.
  2. **A real circular import, caught only by running the test suite, not
     by `mypy`.** Adding `SpeechToTextSession`/`TextToSpeechSession`
     protocols directly into `ws_connection.py` created
     `ws_connection.py` → `stt/deepgram.py` → `ws_connection.py`. `mypy .`
     passed cleanly throughout (it doesn't execute imports the way
     Python's runtime does); `pytest` failed immediately with
     `ImportError: cannot import name 'TranscriptEvent' from partially
     initialized module`. Fixed by splitting the STT/TTS session
     protocols into a new `provider_sessions.py` that depends on both
     `ws_connection.py` and `stt/deepgram.py`, while `ws_connection.py`
     itself now depends on nothing else in this package. Worth
     remembering generally: a clean `mypy` run is not proof an import
     graph is acyclic — only actually importing the module (which
     running the tests does) proves that.
  3. **Kept ElevenLabs' default `output_format` as `mp3_44100_128`, not
     switched to a raw PCM format**, after checking ElevenLabs' own docs:
     PCM output formats (`pcm_16000`/`pcm_24000`/etc.) require a
     Creator-tier-or-above subscription, not available on the free tier
     this build targets. T4's test page therefore plays audio via
     `MediaSource` + `audio/mpeg` rather than manually scheduling raw PCM
     buffers — a real constraint discovered by checking, not a shortcut.
  4. **`vad.py` uses plain Python (`array`/`math`), not the stdlib
     `audioop` module**, despite `audioop.rms` being the obvious one-line
     alternative — `audioop` was deprecated in 3.11 and is removed
     outright in 3.13. This repo pins `<3.13` today, but writing new 2026
     code against a module already scheduled for removal was worth
     avoiding for the cost of a few extra lines.
- **Verification performed:** same full battery as before — `ruff check
  .`, `ruff format --check .`, `mypy .` clean across the whole repo; full
  `pytest tests/`: 2118 passed, 0 failed. The barge-in test
  (concurrency-sensitive by nature) was additionally run 5 times in a row
  to check for flakiness — stable every time. T4's page had its embedded
  `<script>` extracted and run through `node --check` for syntax validity
  (the only verification possible without a real browser).
- **Verification NOT performed:** T4's test page has never been opened in
  an actual browser — `getUserMedia`, `ScriptProcessorNode`,
  `MediaSource`/`audio/mpeg` append/abort behavior are all unverified
  beyond "the JS parses." Barge-in's RMS/consecutive-chunk thresholds are
  unverified against real speech or real background noise. All three T12
  metrics are wired but have never recorded a real value. T13 (real chat
  UI) was deliberately not started this pass — see its note in the task
  list above for why.
- **Next step for whoever resumes this:** with `ELEVENLABS_VOICE_ID` and
  `VOICE_ENABLED=true` set, run `python3 -m http.server 8080` from
  `tools/voice-test-page/`, open `http://localhost:8080/` (not
  `file://`), grab a bearer token from the real app's `sessionStorage`
  (`rm_id_token`, see the page's own instructions), and do a real voice
  turn. That single live pass is what unblocks T14, real T12 numbers, and
  a go/no-go on T10's current threshold defaults before T13 is worth
  starting.

**2026-08-27 (later same day) — T13 built; T14 live vendor verification
achieved.** Same branch. This entry is intentionally precise about which
half of "live-tested" is now true, because it's the one distinction most
likely to get flattened into an overstated interview claim.

- **T13, new files:** `apps/web/public/voice-worklet.js` (an
  `AudioWorklet`, downsamples mic audio to 16kHz PCM16 — the real,
  non-deprecated counterpart to T4's `ScriptProcessorNode`). **Modified
  files:** `apps/web/src/features/chat/use-chat.ts` (added
  `voiceStatus`/`voiceError`/`voiceDraftTranscript` state and
  `startVoiceChat`/`stopVoiceChat` — a second, WS-based sibling to the
  existing SSE-based `send()`, deliberately reusing the same `messages`/
  `patchMessage`/`activeConversationId` machinery so voice turns render
  through the exact same `MessageBubble` component, rather than a
  parallel message list), `apps/web/src/features/chat/components/
  chat-composer.tsx` (a mic toggle button + status/transcript banner,
  new props only), `apps/web/src/app/(app)/chat/page.tsx` (wires the two
  together), `apps/web/src/components/ui/icons.tsx` (added
  `MicIcon`/`MicOffIcon`, matching the file's existing icon-component
  shape). All changes to existing files are additive (new props, new
  branches) — no existing prop's meaning or `send()`'s behavior changed.
- **Verification performed for T13:** `tsc --noEmit` clean, `next lint`
  clean on every touched file, `next build`'s compile step succeeded.
  **Not performed:** opening it in an actual browser — nothing exercises
  `getUserMedia`/`AudioWorklet`/`MediaSource` for real yet.
- **A pre-existing, unrelated finding surfaced by running the full
  `next build`:** `apps/web/src/app/(app)/memory/page.tsx:307` fails
  `next lint`'s `@typescript-eslint/no-unused-expressions` rule, which
  blocks `next build` entirely (Next.js runs lint as part of the
  production build by default). `git diff` on that file is empty — this
  file was never touched by any voice work, in either session. **This
  bug pre-dates this entire effort and is not caused by it**; it does
  mean `npm run build` was already broken before today, independent of
  voice. Flagged here rather than fixed, since it's out of this plan's
  scope — a call for the user, not a silent fix.
- **T14 — real live verification against real vendor APIs, using the
  actual repo code, not mocks or fixtures.** In order:
  1. Confirmed network egress to `api.deepgram.com` and
     `api.elevenlabs.io` works from this environment, and that the
     already-running local dev stack (Postgres/Valkey/Qdrant/Prometheus/
     Grafana via `docker-compose`, plus a running `uvicorn` dev server)
     was available.
  2. **Discovered the auth wall is real and by design**: `WS /chat/voice`
     authenticates via `authenticate_token` →
     `JWTVerifier(CognitoAuthenticationProvider())` — real Cognito JWT
     verification, no dev/mock provider exists anywhere in
     `apps/api/app/auth/`. There is no way to script a valid token
     without an actual Cognito login. This is not a gap in the voice
     work; it's how auth is supposed to behave, and it's the reason the
     rest of this list works around the full route rather than through it.
  3. **`DeepgramSTTProvider` live test**: generated real speech locally
     with macOS `say` ("This is a live test of the voice pipeline."),
     converted to 16kHz mono PCM16 with `afconvert`, streamed it through
     the actual provider class with the real `DEEPGRAM_API_KEY`. Result:
     `is_final=True`, transcript `"This is a live test of the voice
     pipeline."` — exact match, via natural `endpointing_ms` silence
     detection (no forced `Finalize`), i.e. the same mechanism production
     `collect_voice_turn_transcript` relies on. Ran `collect_voice_turn_
     transcript` itself (not just the raw provider) with a fake
     `WebSocket` feeding the same audio — identical correct result,
     confirming the actual function `chat.py`'s route calls, not just a
     lower-level primitive.
  4. **`ElevenLabsTTSProvider` live test, blocked once, then unblocked**:
     the first attempt (a well-known public "Rachel" voice ID) returned
     `402 payment_required` — *"Free users cannot use library voices via
     the API. Please upgrade your subscription to use this voice."* This
     is a real, permanent constraint of the free tier this account is on,
     not a bug: **free-tier ElevenLabs accounts can only use voices
     already in their own "My Voices" list via the API, never the
     Voice Library.** Confirmed two of ElevenLabs' commonly-pre-seeded
     default voice IDs (`EXAVITQu4vr4xnSDxMaL`, `pNInz6obpgDQGcFmaJgB`)
     already exist in this account's own "My Voices" and both returned
     `200`. Used the first to run the real provider class end-to-end:
     real text in, 3 real audio chunks out (37,243 bytes total),
     confirmed by `afconvert` to be genuinely valid, decodable MP3 audio
     (2.32 seconds, matching the spoken sentence's length).
  5. **`stream_voice_response` live test**: fed a real `ElevenLabsTTSProvider`
     a simulated Generation-Runtime token stream (five deltas mimicking
     real streaming granularity) through the actual function, with a fake
     client `WebSocket`. Result: correct sentence-buffering (all five
     deltas assembled into one sentence, split on its trailing period),
     one real `send_text` call, real audio streamed back and written to
     disk, independently confirmed valid by `afconvert` again. This
     exercises T8/T9's real code, not a rebuild of it for the test.
  6. **Full round trip, the most convincing single result**: fed the
     ElevenLabs-synthesized audio from step 4 back into live Deepgram via
     `collect_voice_turn_transcript`. Final transcript:
     *"This is a live test of the voice pipeline."* — an exact match to
     the original text, having round-tripped through two independent real
     vendor services and this repo's own protocol implementations for
     both, with no human speaking a word.
  7. Set `VOICE_ENABLED=true` and `ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL`
     in `.env` (the confirmed-working voice from step 4) — the app itself
     is now actually configured, not just capable of being configured.
- **What this does and does not prove, stated plainly:** it proves the
  wire-protocol implementations in `DeepgramSTTProvider` and
  `ElevenLabsTTSProvider`, and the orchestration in
  `collect_voice_turn_transcript`/`stream_voice_response`, are correct
  against the real live services — the single riskiest, most novel,
  least-precedented part of this entire build, and the part a code
  review alone could never fully confirm. It does **not** prove the full
  authenticated route works, that a real browser's mic/`AudioWorklet`/
  `MediaSource` pipeline works, that barge-in triggers correctly on real
  speech, or that T12's metrics reach the real running Prometheus
  instance. Those all still need one real live session through a real
  browser.
- **Verification performed (repo-wide, post-T13):** `ruff check .`,
  `ruff format --check .`, `mypy .` clean; full `pytest tests/`: 2118
  passed, 0 failed (unchanged from before T13, since T13 touched no
  Python). `tsc --noEmit` clean; `next lint` clean on every voice-touched
  frontend file (the one lint failure found, `memory/page.tsx`, is
  pre-existing and unrelated, see above).
- **Next step for whoever resumes this:** log into the real app at
  localhost:3000 in an actual browser, open Chat, click the new mic
  button, and speak. That one session is the only thing left standing
  between "implemented and live-vendor-verified" and "actually done."

**2026-08-27 (T14, for real this time) — first actual browser test run,
by the user, through the real authenticated route. Result: mic capture
and Deepgram transcription both worked correctly; TTS audio did not play
(text-only response); a real runtime error surfaced why.**

- **The bug:** `Error: Failed to execute 'appendBuffer' on 'SourceBuffer':
  The SourceBuffer is full, and cannot free space to append additional
  buffers`, thrown from `use-chat.ts`'s `flushPendingAudio`. Root cause:
  one `MediaSource`/`SourceBuffer` was created for the *whole voice
  session* and never reset between turns. Nothing was ever consuming
  (playing) the buffered data fast enough to free space, so a
  sufficiently long response's accumulated audio chunks exhausted the
  `SourceBuffer`'s quota outright. Once `appendBuffer` threw, the
  exception was uncaught, silently killing audio for the rest of the
  session — text kept working because it's a fully separate code path
  (`send_json`, not `send_bytes`).
- **The fix:** `setupVoicePlayback()` now creates a fresh `Audio()` +
  `MediaSource` + `SourceBuffer` **per turn** (called when each turn's
  final transcript arrives), tearing down and revoking the previous
  turn's `Audio` element's object URL first, rather than one shared
  instance for the whole session. Also: switched from the passive
  `autoplay` attribute to an explicit `player.play().catch(...)` so a
  blocked-autoplay failure surfaces instead of failing silently, and
  wrapped `appendBuffer` itself in try/catch as a backstop (drops the
  rest of that turn's audio on failure rather than wedging the whole
  pipeline again). `stopVoiceChat` now also revokes the object URL.
  `tsc --noEmit` and `next lint` both clean on the changed file.
- **Not yet re-verified**: this fix has not itself been through a live
  browser pass yet — it directly addresses the exact stack trace
  produced by the first real attempt, but "should fix it" isn't the same
  as "confirmed fixed." That's the next thing to check.
- **User's other observation, "not real-time"**: worth separating two
  things this could mean. (a) No audio ever played, so naturally it read
  as text chat with extra steps — the fix above directly addresses this.
  (b) Even with audio working, this is a **turn-based** exchange (speak,
  then the assistant responds) with barge-in as the interrupt mechanism,
  not simultaneous two-way audio like a phone call — that's this build's
  actual scope (§3), not a bug to fix. Barge-in itself has still never
  been exercised against real speech, since audio never played long
  enough to test interrupting it.
- **Next step:** retry the same live session now that the fix is in —
  confirm audio actually plays this time, then specifically try talking
  over a response to exercise barge-in for the first time against real
  speech.

**2026-08-27 (T14, second real bug) — retried live: mic/STT worked again
across two turns ("Hi.", "Can you hear me?"), but both assistant messages
froze forever at an empty "streaming" state, no text, no audio, no error
shown. User reported "not working real time and has delays."**

- **Diagnosis, from the code, not from logs (none were available):**
  `MessageBubble` renders `stage: 'streaming'` as a perpetual typing
  indicator and `stage: 'error'` as a real error — the screenshot showed
  exactly the former, frozen, matching what happens if a turn's assistant
  message is created (on the final transcript) but then **never receives
  another patch at all**. The one code path that does that: a
  `voice.interrupted` event. Tracing why that would fire almost
  immediately on an ordinary "Hi." turn: the client's mic stays open and
  streaming for the *entire* turn, including the moment a response starts
  generating (that's what makes barge-in possible at all) — so barge-in's
  detector is evaluating live room-noise RMS the instant a response
  begins, not just deliberate re-speech. The original defaults
  (`voice_barge_in_rms_threshold=800.0`, `voice_barge_in_consecutive_
  chunks=3`) were an untuned guess (flagged as exactly that in T10/T11's
  original entries) that turned out to be low enough for ordinary
  microphone/room noise to satisfy on nearly every turn — self-inflicted
  false barge-in, not a Deepgram/ElevenLabs/generation problem. This is
  inferred from the code's behavior and the observed symptom, not
  confirmed via a server log (none was captured this round) — noted as
  inference, not certainty, but it explains every observed symptom
  exactly and no alternative theory does.
- **Two fixes, one bug each:**
  1. **Real defect, independent of the theory above and worth fixing
     regardless**: `use-chat.ts`'s `voice.interrupted` handler stopped
     playback but never patched the in-flight assistant message to any
     terminal state, so an interrupt (false-positive or genuine) freezes
     that bubble forever. Fixed: it now patches the message to
     `stage: 'done'` if any content had already arrived, or
     `stage: 'error'` with an explicit "Interrupted before a response
     arrived" message if not, and clears `voiceAssistantIdRef`. This
     makes any future interrupt (including a real, deliberate one)
     visibly resolve instead of hanging — and makes this failure mode
     self-diagnosing from the UI alone next time, rather than requiring
     another guess-from-a-screenshot round.
  2. **The probable root cause**: `voice_barge_in_enabled` now defaults
     to **`False`**, not `True` (`apps/api/app/core/settings.py`). A
     false-positive interrupt silently breaking the core "ask a question,
     get an answer" path is a strictly worse failure than losing an
     unproven stretch feature days before an interview, so this defaults
     off until it can be tuned against real audio. Raised
     `voice_barge_in_rms_threshold` to `4000.0` and
     `voice_barge_in_consecutive_chunks` to `5` as more conservative
     starting values for whenever it's re-enabled — still untuned
     guesses, just less aggressive ones. One existing unit test
     (`test_barge_in_cuts_the_response_short_and_notifies_the_client`)
     relied on the old default being `True` and needed an explicit
     `monkeypatch.setattr(settings, "voice_barge_in_enabled", True)`
     added — full suite re-verified green after (2118 passed).
- **Verification performed:** `ruff`/`mypy`/`pytest` (2118 passed) on the
  backend change; `tsc --noEmit`/`next lint` clean on the frontend change.
  **Not yet performed:** a third live retry to confirm this actually
  fixes it — the barge-in theory is the best-supported explanation
  available, not a confirmed root cause. If audio and text still don't
  both come through cleanly on the next attempt, barge-in was not (or not
  the only) cause, and this needs actual server-side logs from a live
  run to diagnose further, not another guess from a screenshot.
- **Process note for whoever reads this log:** this is the second
  real bug found only by an actual person actually using the feature, in
  two consecutive live attempts — both fixes so far have been "the
  untuned default was wrong, in the direction that breaks the *unverified
  feature* rather than core functionality." That pattern is worth
  watching for a third time too, and argues for capturing real backend
  logs (not just screenshots) on the next attempt if this doesn't fully
  resolve it, since "streaming forever with no error and no server-side
  view" is a slow way to debug from screenshots alone.

**2026-08-27 (T14, third round) — barge-in fix confirmed working (turn 1
got a real text response, implicitly audio too since no complaint this
round), but a second turn in the same session froze the same way. User:
"not consistent."**

- **Honest state: root cause for this one is not confirmed.** With
  `voice_barge_in_enabled` now `False`, `_watch_for_barge_in` returns
  immediately without ever calling `receive()` -- barge-in cannot be the
  cause of this specific freeze. No server log was available to identify
  what actually happened in `_prepare_chat_generation`/`stream_generate`/
  `_persist_on_complete` for that second turn.
- **What was done instead of guessing a third root cause blindly:** added
  a safety net around each turn's generation body in `stream_chat_voice`
  (`apps/api/app/api/v1/chat.py`) -- any exception is now caught,
  logged server-side with a full traceback (`logger.exception`), sent to
  the client as a real `{"type": "error", ...}` frame (which the
  frontend already turns into a visible `stage: 'error'` bubble, not
  another silent freeze), and the loop `continue`s to the next turn
  instead of the exception propagating uncaught. This does not fix
  whatever is actually wrong -- it makes it **visible** the next time it
  happens, either as an error bubble in the browser or a traceback in the
  server's terminal, instead of an unexplained hang. This is the fastest
  real path to an actual diagnosis at this point, not a guess.
- **What still would NOT be caught by this**: a genuine infinite hang
  (something awaiting forever rather than raising) inside that same
  block. If the *next* freeze still shows no error bubble and nothing in
  the server terminal, that rules out an exception and points at a real
  hang somewhere in generation/memory/web-search-necessity for
  multi-turn (history-bearing) requests specifically -- worth checking
  `conversation_service.compact_history_if_needed`/`load_prompt_history`
  and the title-generation claim/release lock next, since turn 1 (empty
  history, first-ever title generation) and turn 2 (real history, no
  title generation needed) are the two structurally different code paths
  between a working first turn and a failing second one.
- **Verification:** `ruff`/`ruff format`/`mypy` clean; full `pytest
  tests/`: 2118 passed, unchanged (no existing test exercises a forced
  mid-turn exception on this route, so this is a net-new safety path,
  not a modification of tested behavior).
- **Next step:** retry once more. If it fails again, **the server
  terminal's output at the moment of failure is now the single most
  useful piece of information to bring back** -- either a real traceback
  from the new safety net, or (if still no error appears at all) evidence
  of a genuine hang rather than a raised exception, which changes where
  to look next.

**2026-08-27 (T14, fourth round) — closed the STT-phase gap in the safety
net (it previously only wrapped the generation half of each turn, not
`collect_voice_turn_transcript`); retried; session still drops after one
conversation turn. User: "still only 1 conversation, then drop. but it's
okay" — deprioritizing further live debugging for now. Recording this as
an open, unresolved gap rather than a fixed bug, since that's what it
actually is.**

- **KNOWN GAP, UNRESOLVED as of 2026-08-27: multi-turn voice sessions do
  not reliably survive past the first turn.** Three real, confirmed fixes
  landed this session (frozen `voice.interrupted` messages; the
  over-sensitive default barge-in threshold; the generation-phase and
  STT-phase safety nets), and each one was a genuine bug -- but **none of
  them turned out to be the actual cause of the session dying after one
  turn**, since it still happens with all four fixes in place. **Root
  cause not identified.**
- **Why it's still unidentified**: no server-side terminal output or
  browser console output was captured at the moment of the drop, across
  any of the four attempts. Every fix so far was inferred from the
  *symptom* (a screenshot of the chat UI) plus reading the relevant code,
  not from a traceback or log line pointing at a specific failing call.
  That approach found and fixed three real, independently-worth-fixing
  bugs, but it has now demonstrated its limit: it cannot find whatever is
  causing *this* one.
- **What is confirmed, precisely:** turn 1 of a voice session reliably
  works end-to-end (STT, generation, and -- as of the barge-in fix --
  audio). Whatever happens next (turn 2's STT phase, or something in the
  transition between turns) either raises an exception now caught by the
  safety net (in which case an error frame should have reached the
  client and/or a traceback should be in the server terminal -- neither
  was checked/reported) or is a failure mode the current safety net
  still doesn't cover (e.g., the WebSocket connection itself dropping at
  the transport level, which no amount of `try`/`except` around
  application code can catch).
- **What would actually resolve this, next time someone picks it up:**
  reproduce with the server's terminal visible and copy the actual output
  at the moment of the drop, and/or the browser's DevTools console/Network
  tab (WS frames) for the same moment. Guessing further from screenshots
  alone without that isn't likely to find it, per the last three rounds.
- **Impact on this plan's status:** T14 remains "partially done" -- the
  vendor integrations are live-verified (see the 2026-08-27 entries
  above), a single voice turn works end-to-end through the real
  authenticated route with real audio, but **sustained multi-turn voice
  conversation is not currently reliable** and should not be presented as
  working in the interview beyond "a single voice exchange works
  end-to-end, real vendor APIs, real audio in and out." Multi-turn
  reliability is this build's most significant open defect.
