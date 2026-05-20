# Saymo

## What This Is

Saymo is a fully local macOS voice assistant that listens to live calls,
detects when the user is addressed, and speaks into the meeting through a
virtual microphone using the user's cloned voice. It is for a user who wants a
local, controllable assistant for standups, Q&A, and takeover moments without
cloud voice APIs. It can now turn captured call audio into local meeting
memory and a reviewable answer cockpit, so the user can see why Saymo thinks
they were addressed, inspect a grounded draft, and decide whether to speak,
edit, skip, or take over.

## Core Value

Saymo must reliably catch when the user is expected to answer and respond fast
enough that the call still feels live.

## Current State

Saymo has shipped milestone v1.4 Live Conversation Memory + Answer Cockpit. The
product can build local transcript ledgers from captured sessions, search and
ask questions about those sessions with transcript citations, generate pending
answer drafts grounded in meeting memory and configured sources, and record
explicit cockpit actions plus sanitized audit trails.

**Status:** v1.4 archived on 2026-05-20. No active milestone is selected.

**Next milestone:** start with `$gsd-new-milestone` when the next product goal
is chosen.

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

### Active

(None — start the next milestone with `$gsd-new-milestone`.)

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
- Auto-speaking generated answer drafts without explicit approval — v1.4
  records approval in the cockpit but does not automatically play generated
  draft text.
- Native macOS capture without BlackHole — useful future work, but separate
  from the local memory/cockpit loop.

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
- GitHub ecosystem review found that local meeting assistants are usually
  strong at transcription, summaries, search, or meeting bots, while Saymo's
  differentiating direction is a local "listen and answer as me" flow with
  explicit user approval and source-backed answer drafts.

## Constraints

- **Platform:** macOS with BlackHole and Chrome-based call providers — existing
  routing model and provider abstractions should stay intact.
- **Privacy:** Captured samples and metadata stay local under `~/.saymo/`; real
  config and recordings must not be committed.
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
| Keep generated-draft playback approval-only for now | Approval/audit is safer than wiring new generated text directly into live playback before more live testing | — Pending |

---
*Last updated: 2026-05-20 after archiving milestone v1.4*
