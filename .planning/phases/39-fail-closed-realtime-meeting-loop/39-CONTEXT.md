---
phase: 39-fail-closed-realtime-meeting-loop
type: context
status: ready_for_research
created: 2026-07-08
autonomous: true
requirements: [REAL-01, REAL-02, REAL-03, REAL-04, REAL-05, REAL-06]
depends_on:
  - 36-call-ready-preflight-and-cache-gate
  - 37-provider-and-audio-remediation
  - 38-local-call-control-daemon-and-launchagent
---

# Phase 39 Context: Fail-Closed Realtime Meeting Loop

## Goal

Make realtime startup and automatic speaking use the shared launch-readiness
contract, then fail closed whenever cache, cloned voice, provider, fallback, or
handbrake state becomes unsafe.

## Approved Design Direction

Use the Phase 36-38 readiness and control contracts as the safety boundary for
realtime mode:

- `saymo auto` remains the primary workflow; new aliases may wrap it, but they
  must share the same launch gate.
- Realtime startup must check the selected profile/provider through
  `collect_launch_readiness()` before capture, STT, provider control, or local
  hotkey registration starts.
- Automatic answers may play only from an approved response-cache hit whose
  cloned-voice metadata is current.
- Cache misses, stale cloned-voice metadata, disabled response cache, blocked
  voice selector, unsafe fallback, provider loss, manual takeover,
  hard-disable, disabled auto-answer, or deterministic addressing skip must
  block automatic playback.
- Explicit manual prepared-standup playback remains allowed through the
  existing `speak`/manual hotkey path when the handbrake state allows it, but
  that manual path must not become the automatic cache-miss fallback.
- Realtime decision output and audit/evidence must use sanitized reason labels
  only, not raw transcripts, generated answers, audio bytes, daily-note
  content, or secrets.

## Grey Areas Resolved By Assumption

### Launch Gate Strictness

- `saymo auto` should require a passed launch-readiness report by default.
- A future explicit bypass can be considered later, but Phase 39 should not add
  a casual unsafe bypass that undermines the milestone.
- The launch gate should report the same grouped remediation as `saymo
  call-ready` so users fix blockers from one source of truth.
- The gate should run before expensive or stateful realtime setup.

### Automatic Response Policy

- Automatic Q&A output must be response-cache-only for v1.9.
- Existing live LLM/TTS fallback paths are allowed only outside automatic live
  playback or behind explicit future opt-in work; for this phase, automatic
  cache miss means blocked.
- Fallback standup audio remains an explicit manual action, not an automatic
  answer to a question.
- Voice selector or metadata blockers must prevent automatic playback even if
  an audio file exists.

### Runtime Provider And Handbrake Policy

- Provider loss should be rechecked before playback, not only at startup.
- Handbrake state is checked both before answer resolution and immediately
  before playback.
- Manual takeover, hard-disable, and auto-answer-off are authoritative; neither
  classifier output nor LLM wording can override them.
- When a trusted call-control daemon owns hotkeys, local `saymo auto` hotkeys
  should be disabled through the Phase 38 seam to avoid duplicate delivery.

### Decision Evidence

- Decision reasons should be small stable labels such as
  `launch-readiness-blocked`, `response-cache-hit`, `cache-miss-blocked`,
  `fallback-blocked`, `provider-blocked`, `handbrake-blocked`,
  `manual-standup-requested`, `addressing-skip`, and `deterministic-skip`.
- Evidence must preserve operational facts and paths, but not the raw transcript
  window or generated answer text.
- Phase 39 should add enough local tests/events for Phase 40 scorecards and
  safety-soak to consume later, without building the Phase 40 reporting layer.

## Existing Building Blocks

- `saymo.analysis.launch_readiness`
  - `collect_launch_readiness`, `LaunchReadinessReport`, grouped remediation,
    sanitized JSON artifacts.
- `saymo.analysis.launch_cache`
  - response-cache coverage and cloned-voice metadata checks.
- `saymo.analysis.response_cache`
  - `ResponseCache`, `build_library`, cached variant lookup.
- `saymo.tts.selector`
  - cloned voice selector and approval policy used by launch checks.
- `saymo.commands.core`
  - `saymo auto`, `_auto`, `_resolve_auto_response_decision`,
    `_automatic_speaking_allowed`, `_request_manual_speak`,
    `_play_cached_audio`, `_control_command_loop`.
- Phase 38 control daemon
  - call-control LaunchAgent status rows, reachability probe, command/audit
    correlation, and duplicate-hotkey prevention seam.

## Required User-Facing Outcomes

1. `saymo auto -p <profile>` starts only after the shared call-ready gate passes
   for source, cache, cloned voice, provider/audio, and call-control handbrake.
2. Any realtime alias or call-start wrapper uses the same launch gate and
   remediation output.
3. Automatic question handling never speaks on response-cache miss, stale voice
   metadata, unsafe fallback, provider loss, manual takeover, hard-disable, or
   disabled auto-answer.
4. Explicit manual prepared-standup playback still works when allowed, but does
   not make automatic cache misses speak.
5. The operator can see sanitized realtime decision reasons for spoke, skipped,
   and blocked outcomes.
6. Deterministic addressing and handbrake state remain the safety boundary; ML
   assistance cannot override a deterministic skip or handbrake block.

## Guardrails

- Do not synthesize or play generated fallback audio automatically on a cache
  miss in Phase 39.
- Do not move provider repair, audio route mutation, or Chrome destructive
  actions into realtime startup.
- Do not weaken manual takeover, hard-disable, auto-answer-off, or
  deterministic addressing gates.
- Do not store raw transcripts, generated answers, daily-note content, audio
  bytes, or secrets in realtime decision evidence.
- Do not change the Phase 38 daemon into the realtime owner; the daemon remains
  control-plane only.

## Suggested Module Boundaries

- `saymo.analysis.realtime_gate`
  - launch-gate evaluation helpers for auto/realtime startup and blocked
    reason rendering.
- `saymo.analysis.realtime_policy`
  - response decision policy for cache-hit vs blocked automatic output, plus
    stable reason labels.
- `saymo.commands.core`
  - thin integration points around `_auto`, `_resolve_auto_response_decision`,
    provider recheck before playback, handbrake checks, and decision audit.
- Existing launch readiness, response cache, voice selector, live-control, and
  call-control modules should be reused rather than duplicated.

## Validation Strategy

- Unit tests for launch-gated `saymo auto` startup with passed and blocked
  readiness reports.
- Unit tests for response-cache-only automatic decisions: hit speaks, miss
  blocks, stale/unsafe fallback blocks, manual speak remains explicit.
- Tests for provider loss and handbrake changes immediately before playback.
- CLI tests proving remediation output is reused and no default unsafe bypass is
  introduced.
- Static tests/greps ensuring fail-closed paths do not record raw private text,
  synthesize live fallback automatically, mutate provider state destructively,
  or bypass deterministic addressing.

## Deferred Ideas

- Phase 40 will turn realtime decision events into richer artifacts,
  scorecards, and safety-soak gates.
- Guarded live LLM/TTS fallback remains future work after latency, approval,
  source-grounding, and voice-quality evidence justify it.
- Automatic provider repair remains future work behind explicit commands and
  provider-specific tests.
