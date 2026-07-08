# Saymo

## What This Is

Saymo is a fully local macOS voice assistant that listens to live calls,
detects when the user is addressed, and speaks into the meeting through a
virtual microphone using the user's cloned voice. It is for a user who wants a
local, controllable assistant for standups, Q&A, and takeover moments without
cloud voice APIs. It can now turn captured call audio into local meeting
memory and a reviewable answer cockpit, so the user can see why Saymo thinks
they were addressed, inspect a grounded draft, and decide whether to speak,
edit, skip, or take over. It also has a local live-control handbrake with
documented hotkeys, a terminal control surface, and explicit safety state for
turning auto-answer off, stopping playback, and taking the microphone back. It
can now rehearse the live loop before a call, produce sanitized session
scorecards, show targeted remediation, and run a local safety soak gate before
trusting auto-answer again.

## Core Value

Saymo must reliably catch when the user is expected to answer and respond fast
enough that the call still feels live.

## Current State

Saymo has shipped milestone v1.8 Call-ready Voice Clone. The product can build
local transcript ledgers from captured sessions, search and ask questions about
those sessions with transcript citations, generate pending answer drafts
grounded in meeting memory and configured sources, record explicit cockpit
actions plus sanitized audit trails, review real captured sessions, reduce
incidental name-handoff false positives, bootstrap speaker labels, play only
approved generated drafts, and replay saved sessions as local regression
fixtures.

It can expose an operator handbrake during live calls: guide, hotkey doctor,
local control panel, scriptable action queue, shared runtime state, expanded
global hotkeys, and audit events for stop/toggle/takeover/skip/status actions.
It can also prove the live loop repeatedly: `saymo rehearsal` performs a
pre-call dry run, `saymo session-scorecard` exports sanitized reliability
evidence, remediation hints explain the next action, and `saymo safety-soak`
turns rehearsal/scorecard artifacts into a local pass/fail gate with baseline
drift checks.

The v1.8 voice-clone path added read-only local model inventory, protected
voice profiles, F5 benchmark evidence, purpose-specific voice selection,
metadata-backed cache freshness checks, preview approval, and safety-soak voice
readiness gates. The active local config now uses the approved `f5tts_clone`
path for the `personal` profile, and a launchd helper can create the missing
Obsidian daily note before standup preparation.

**Status:** v1.9 Call Launch Readiness started on 2026-07-08.

The next milestone focuses on making the full pre-call and live-call path feel
operationally reliable: one green launch path, provider/tab remediation,
prepared response cache health, realtime loop readiness, and a local
daemon/control surface so the handbrake does not depend on a terminal window.

## Current Milestone: v1.9 Call Launch Readiness

**Goal:** Make Saymo reliably go from daily note and prepared cloned-voice
cache to a controlled realtime call loop with provider readiness, launchd
health, and handbrake controls verified before the meeting starts.

**Target features:**
- One call-ready command or flow that checks/creates the daily note, prepares
  standup audio and response-cache variants, validates cloned voice cache
  metadata, and reports only actionable blockers.
- Provider readiness checks and remediation for Glip/Chrome tab state,
  BlackHole routing, playback/capture devices, permissions, and stale launchd
  helpers.
- A local Saymo call-control daemon or LaunchAgent that keeps global hotkeys,
  live-control state, status, and stop/takeover actions available outside the
  terminal.
- A realtime meeting loop that starts only after cloned voice, response cache,
  provider, handbrake, and profile readiness pass, and that fails closed on
  cache miss or unsafe fallback.
- Post-call/rehearsal evidence that shows whether the launch and realtime loop
  stayed healthy, with regressions feeding back into preflight and safety-soak.

## Last Completed Milestone: v1.8 Call-ready Voice Clone

**Goal:** Make Saymo speak in the user's cloned voice through a reproducible,
local, call-ready pipeline with clear quality, latency, fallback, and safety
evidence.

**Delivered:**
- Read-only local voice model inventory and protected profile manifests for
  samples, transcripts, training datasets, and runtime assets.
- Repeatable F5 benchmark artifacts with manifests, blind review templates,
  review scoring, and benchmark-backed approval.
- Candidate gates for Qwen3 Base and heavier engines that prevent accidental
  installs, downloads, runtime promotion, or training.
- Purpose-specific call-ready voice selector and fallback chain for prepare,
  response cache, preview, realtime, and approved live-call output.
- Preview, A/B approval, preflight, rehearsal, scorecard, and safety-soak gates
  that block stale, unapproved, or non-cloned live-call output.

## Previous Milestone: v1.7 Live Reliability Rehearsal

**Goal:** Turn real and rehearsal sessions into a repeatable reliability loop
that shows whether Saymo is safe enough for the next call and what to fix when
it is not.

**Delivered:**
- Guided pre-call rehearsal that exercises capture, triggers, handbrake,
  playback gates, and local control state without needing a real meeting.
- Session reliability scorecard that combines trigger, addressing, speaker,
  playback, latency, and handbrake audit evidence.
- Remediation hints that turn failed checks into concrete config, permission,
  audio-device, review, and retest actions.
- Safety soak/replay gate over saved rehearsals and scorecards with baseline
  drift checks and nonzero failure exit.

## Previous Milestone: v1.6 Live Control Handbrake

**Goal:** Give the user a clear local handbrake for live calls: controls and
macOS hotkeys that turn auto-answer on/off, stop speech, enter manual takeover,
and explain exactly what state Saymo is in.

**Delivered:**
- Short operator guide for safe live-call control.
- Shared live-control state model and local command/audit files.
- Local handbrake panel plus scriptable `live-control-action`.
- Expanded configurable macOS hotkeys for primary and optional actions.
- `hotkey-doctor` diagnostics and focused safety regressions.

## Previous Milestone: v1.5 Live Review + Safe Approved Speak

**Goal:** Make the live loop reliable after real call recordings by improving
post-call review, handoff detection, speaker bootstrapping, approved draft
playback, and regression replay.

**Target features:**
- Prioritized post-call review queue for handoffs, questions, mentions, and
  speaker/decision labels.
- Addressing v2 that separates direct handoffs from incidental name mentions.
- Speaker bootstrap workflow that reduces `unknown` coverage without requiring
  always-on diarization.
- Approved draft playback through existing TTS/playback safety paths.
- Regression replay over saved sessions with false-positive, missed-handoff,
  question-noise, and speaker-coverage metrics.

## Requirements

### Validated

- ✓ Local voice playback into calls through BlackHole routing exists before
  this milestone.
- ✓ Manual hotkeys and takeover checks exist before this milestone.
- ✓ `saymo trigger-capture` can save classified call windows as WAV plus JSON
  metadata before this milestone.
- ✓ Faster catch path is measurable and tunable per profile.
- ✓ Faster say path is preflighted and measured before calls.
- ✓ Captured trigger samples feed a repeatable tuning/evaluation workflow.
- ✓ v1.0 Speedly Catcher + Speedly Sayer completed and merged on 2026-05-15.
- ✓ Captured trigger samples can carry local speaker labels and evaluation
  groups results by `me`, `other`, and `unknown`.
- ✓ Accepted/rejected sample labels can train a local classifier that runs in
  shadow mode for `trigger-eval` and `trigger-check`.
- ✓ Plain name mentions are separated from true handoffs via `mentioned_me` and
  `asked_to_speak` sample categories.
- ✓ Active-call provider probes can report segmented latency and export local
  JSON/Markdown history by profile/provider.
- ✓ User can treat one live recording run as a named training session and
  review its saved samples together.
- ✓ User can correct category, speaker, and answer-decision labels in bulk from
  CLI review commands.
- ✓ User can see whether the local classifier has enough balanced evidence to
  be trusted as a live-call assist, while deterministic gating remains the
  safety boundary.
- ✓ User can run optional local diarization on a completed trigger-capture
  session without making cloud services or heavy ML packages mandatory.
- ✓ User can inspect diarization speaker clusters and map them to
  `me`/`other`/`unknown` labels for the current profile/session.
- ✓ User can review and promote speaker suggestions into existing trigger
  sample metadata while preserving manual overrides.
- ✓ User can evaluate speaker-label quality before using suggested labels in
  classifier readiness or training.
- ✓ User can treat a captured call as a local transcript ledger, not only
  isolated trigger samples.
- ✓ User can search and ask questions about a current or past local meeting and
  get cited answers from stored transcript evidence.
- ✓ User can generate and review a grounded answer draft before Saymo speaks
  into the call.
- ✓ User can inspect an audit trail explaining each trigger, draft, action, and
  spoken response.
- ✓ User can review a completed call through a prioritized queue that moves
  likely handoffs, questions, name mentions, and unlabeled speaker windows to
  the top.
- ✓ User can see post-call review progress with unknown speaker counts,
  answer-decision coverage, accepted/rejected labels, and classifier-readiness
  blockers.
- ✓ User can correct false handoffs where Saymo treats an incidental name
  mention as a request to speak.
- ✓ User can tune per-profile handoff and mention-only addressing patterns.
- ✓ User can bootstrap enough speaker labels from a completed session that
  classifier readiness can distinguish `me`, `other`, and `unknown`.
- ✓ User can approve a generated draft and have Saymo play only that approved
  text through the existing local TTS/playback path with preview, timeout, and
  audit.
- ✓ User can replay a saved session as a regression fixture and see whether
  addressing, question detection, and speaker coverage improved.
- ✓ User can use a simple guide to know which button or hotkey to press during
  a live call emergency.
- ✓ User can toggle auto-answer on/off without killing the call or losing the
  ability to answer manually.
- ✓ User can see the current live-control state before trusting Saymo to speak.
- ✓ User can verify macOS hotkeys and permissions before joining a call.
- ✓ User can run a local pre-call rehearsal that proves capture, trigger,
  hotkey, handbrake, and playback gates before joining a real call.
- ✓ User can inspect one reliability scorecard for a real or rehearsal session.
- ✓ User can get concrete remediation steps when readiness, reliability, or
  safety checks fail.
- ✓ User can run a repeatable safety soak/regression gate before trusting
  Saymo in another meeting.

### Active

- User can run one call-ready path that creates missing Obsidian daily notes,
  prepares standup audio, builds response-cache variants, validates cloned
  voice metadata, and returns a concise ready/not-ready result.
- User can see provider, Chrome tab, BlackHole, permission, profile, cache, and
  launchd helper blockers with exact remediation and rerun commands.
- User can start, stop, inspect, and recover a local call-control daemon or
  LaunchAgent that keeps hotkeys and live-control state active outside the
  terminal.
- User can start a realtime meeting loop only after cloned voice, response
  cache, provider, handbrake, trigger, and profile readiness pass.
- User can inspect post-call or rehearsal evidence for launch health, live-loop
  decisions, cache hits/misses, handbrake actions, and unsafe fallback blocks.

### Out of Scope

- Cloud STT/TTS as a required path — the product remains local-by-default.
- Full autonomous meeting participation — Saymo assists with prepared answers
  and addressed questions, but manual takeover remains supported.
- Training a new voice model from call recordings in this milestone — captured
  call audio is for trigger and routing behavior, not voice-clone training.
- Required automatic diarization model installation — v1.3 must keep
  diarization engines optional and disabled until configured.
- Real-time live-call diarization in `saymo auto` — this milestone focuses on
  offline captured sessions so latency and false-positive risk stay bounded.
- Auto-speaking generated answer drafts without explicit approval — v1.5 may
  play explicitly approved drafts, but unapproved generated text must never
  reach the call.
- Native macOS capture without BlackHole — useful future work, but separate
  from the local memory/cockpit loop.
- Polished App Store-style native menu bar packaging — v1.9 may add a local
  daemon/LaunchAgent and lightweight status/control surface, but productized
  native UI distribution is separate work.
- Using real call recordings as voice-clone training data — call audio is for
  trigger/reliability review, not voice identity training, unless explicitly
  exported by the user in a future milestone.

## Context

- Current stack: Python CLI, Click commands, faster-whisper, Ollama, local TTS
  engines, BlackHole routing, and Chrome provider automation.
- Live-call risk areas are latency, false positives when a name is merely
  mentioned, missed trigger variants from Whisper, and manual recovery when the
  user wants to answer themselves.
- Recent work added trigger diagnostics, fuzzy trigger learning, manual
  takeover hotkeys, trigger confirmation, response cache routing diagnostics,
  classified trigger sample capture, session-ledger review, classifier
  readiness, optional offline speaker diarization review, local meeting memory,
  cited meeting ask, answer drafts, and answer-cockpit audit trails.
- The first long v1.4-era real recording saved 507 transcript windows with
  complete coverage, but all speaker labels remained `unknown`; classifier
  readiness reported `not_ready` because no accepted/rejected labels exist.
- The same recording produced two `asked_to_speak` candidates that are likely
  false positives: one incidental first-name mention and one full-name/surname
  mention. These should be regression cases for Addressing v2 without
  committing raw transcript text.
- GitHub ecosystem review found that local meeting assistants are usually
  strong at transcription, summaries, search, or meeting bots, while Saymo's
  differentiating direction is a local "listen and answer as me" flow with
  explicit user approval and source-backed answer drafts.

## Constraints

- **Platform:** macOS with BlackHole and Chrome-based call providers — existing
  routing model and provider abstractions should stay intact.
- **Privacy:** Captured samples and metadata stay local under `~/.saymo/`; real
  config and recordings must not be committed.
- **Training data safety:** Existing `.saymo` training datasets and model
  checkpoints are expensive to recreate; audit and read them by default, mutate
  only behind explicit user commands.
- **Latency:** Optimizations must preserve answer gating quality; faster false
  positives are worse than slower correct skips.
- **Configurability:** Profile-specific knobs belong in `config.yaml` or
  documented CLI flags, not hardcoded private names.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep live-call listening local-first | Avoid leaking meeting audio and preserve offline operation | ✓ Good |
| Use classified trigger samples before deeper ML changes | Real misses/false positives are the best tuning data | ✓ Implemented via `trigger-eval` |
| Separate catch latency from say latency | Different bottlenecks require different measurements and tests | ✓ Implemented in `saymo auto` diagnostics |
| Use speaker labels as sidecars first | Avoid forcing a diarization dependency while still enabling speaker-aware evaluation | ✓ Implemented in Phase 5 |
| Run classifier in shadow mode before enabling it | Protect live calls from unproven learned behavior | ✓ Implemented in Phase 6 |
| Separate name mentions from handoffs deterministically | Plain mentions should train/tune differently from moments where Saymo should answer | ✓ Implemented after real sample review |
| Measure providers through the existing abstraction | Keep provider latency work scoped to Chrome call automation, not UI redesign | ✓ Implemented in Phase 7 |
| Require a readiness gate before live classifier assist | Learned behavior should be opt-in and evidence-backed per profile | ✓ Implemented in Phase 10 |
| Keep diarization optional and review-first | Speaker suggestions are useful only after the user can inspect and correct them locally | ✓ Implemented in v1.3 |
| Build answer cockpit before autonomous speaking | The user must be able to inspect trigger evidence and approve a draft before Saymo talks in a live call | ✓ Implemented in v1.4 |
| Use real recorded sessions as regression fixtures | False positives and unknown-speaker coverage are visible only against actual call audio | Implemented in v1.5 |
| Wire only approved generated drafts into playback | Approval/audit is the safety boundary; generated text may play only after an explicit user action | Implemented in v1.5 |
| Prefer an explicit handbrake over hidden automation | During live calls, the user needs visible control and fast recovery more than another autonomous behavior | Implemented in v1.6 |
| Prove the live loop before trusting it | The next risk is not missing controls, but not knowing whether the whole loop is reliable for the next meeting | Implemented in v1.7 |
| Treat voice-clone assets as protected local state | Model checkpoints and training datasets are costly to redownload or retrain, so cleanup/training must be explicit and auditable | Implemented in v1.8 |
| Treat call launch as one green path | Daily note, prepare/cache, provider tab, voice readiness, and handbrake state fail in different places unless the operator sees one actionable readiness result | Pending in v1.9 |

---
*Last updated: 2026-07-08 after starting milestone v1.9*
