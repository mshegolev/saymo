# Milestones

## Current

### v1.11 F5 Gap Hardening

**Started:** 2026-07-09
**Status:** Active

Focus: close the remaining F5 silent-breath hardening gaps around direct cache
staleness tests, continuation-pause coverage, and no-audible-breath guards.

Active artifacts:
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`

## Completed

### v1.10 Silent Breath Natural Pacing

**Started:** 2026-07-09
**Completed:** 2026-07-09
**Archived:** 2026-07-09
**Status:** Complete

Focus: keep F5 natural pacing human-like without transmitting audible breath,
hum, or buzz into the meeting microphone.

Delivered:
- F5 natural pacing now uses silent pauses instead of audible breath splices.
- Sentence, clause, paragraph, and continuation pauses remain configurable.
- F5 pacing knobs are included in selector/cache fingerprints, so stale
  prepared and response cached WAVs are rejected after timing changes.
- Regression tests prove zero-valued breath pauses and cache fingerprint
  invalidation.
- Local preview generated at
  `~/.saymo/voice_benchmarks/20260709-silent-breath/f5tts-silent-breath-01.wav`.

Archives:
- `.planning/milestones/v1.10-ROADMAP.md`
- `.planning/milestones/v1.10-REQUIREMENTS.md`
- `.planning/milestones/v1.10-MILESTONE-AUDIT.md`
- `.planning/milestones/v1.10-phases/`

### v1.9 Call Launch Readiness

**Started:** 2026-07-08
**Completed:** 2026-07-08
**Archived:** 2026-07-08
**Status:** Complete

Focus: make Saymo reliably go from daily note and prepared cloned-voice cache
to a controlled realtime call loop with provider readiness, LaunchAgent health,
and handbrake controls verified before the meeting starts.

Delivered:
- One call-ready launch gate for daily note, prepared standup audio,
  response-cache coverage, cloned-voice metadata, and actionable remediation.
- Provider and audio readiness for Glip/Chrome, BlackHole routing, microphone
  takeover, permissions, and non-destructive remediation.
- Local call-control daemon and per-profile LaunchAgent for hotkeys,
  heartbeat, live-control status, and stop/takeover actions outside the
  terminal.
- Fail-closed realtime meeting loop that blocks cache misses, stale voice
  metadata, unsafe fallback, provider loss, and handbrake-disabled states.
- Sanitized launch/realtime evidence feeding rehearsal, scorecards,
  troubleshooting, and safety-soak.

Archives:
- `.planning/milestones/v1.9-ROADMAP.md`
- `.planning/milestones/v1.9-REQUIREMENTS.md`
- `.planning/milestones/v1.9-MILESTONE-AUDIT.md`
- `.planning/milestones/v1.9-phases/`

### v1.8 Call-ready Voice Clone

**Started:** 2026-07-07
**Completed:** 2026-07-07
**Archived:** 2026-07-07
**Status:** Complete

Focus: make Saymo's cloned voice usable for the real live-call path through a
local, auditable voice pipeline with model inventory, repeatable benchmarks,
safe fallback behavior, and preview/approval before real-call use.

Delivered:
- Read-only voice inventory and protected profile manifests for existing local
  voice samples, transcripts, training datasets, and F5 runtime assets.
- F5 benchmark artifacts with WAV clips, manifest, blind review template,
  review scoring file, and score report.
- Candidate gates that keep Qwen3 Base and heavier engines behind baseline,
  transcript, isolated install, and no-runtime-promotion boundaries.
- Runtime voice selector and cache metadata that block stale, unapproved, or
  non-cloned live-call output by default.
- Preview, approval, preflight, rehearsal, scorecard, and safety-soak gates for
  call-ready voice use.

Archives:
- `.planning/milestones/v1.8-ROADMAP.md`
- `.planning/milestones/v1.8-REQUIREMENTS.md`
- `.planning/milestones/v1.8-MILESTONE-AUDIT.md`
- `.planning/milestones/v1.8-phases/31-voice-asset-inventory-and-profile-setup/`
- `.planning/milestones/v1.8-phases/32-benchmark-scoring-and-f5-baseline/`
- `.planning/milestones/v1.8-phases/33-candidate-shootout-gates/`
- `.planning/milestones/v1.8-phases/34-call-ready-engine-selector-and-fallback-chain/`
- `.planning/milestones/v1.8-phases/35-preview-a-b-approval-and-safety-soak/`

### v1.7 Live Reliability Rehearsal

**Started:** 2026-05-22
**Completed:** 2026-07-07
**Archived:** 2026-07-07
**Status:** Complete

Focus: turn real and rehearsal sessions into a repeatable reliability loop that
shows whether Saymo is safe enough for the next call and what to fix when it is
not.

Delivered:
- Guided pre-call rehearsal for capture, triggers, handbrake, playback gates,
  and local control state.
- Session reliability scorecard for trigger, addressing, speaker, playback,
  latency, and handbrake audit evidence.
- Remediation hints for failed config, permissions, audio-device, review, and
  safety checks.
- Safety soak/replay checks that run saved sessions and rehearsals as a local
  regression gate.

Archives:
- `.planning/milestones/v1.7-ROADMAP.md`
- `.planning/milestones/v1.7-REQUIREMENTS.md`
- `.planning/milestones/v1.7-MILESTONE-AUDIT.md`
- `.planning/milestones/v1.7-phases/`

### v1.6 Live Control Handbrake

**Started:** 2026-05-22
**Completed:** 2026-05-22
**Archived:** 2026-05-22
**Status:** Complete

Focus: give the user an obvious live-call handbrake: short operator guidance,
visible buttons, macOS hotkeys, auto-answer on/off state, manual takeover, and
verification that Saymo cannot speak unexpectedly while disabled.

Delivered:
- Short guide for operating Saymo during a live call and emergency recovery.
- Shared live-control state and command queue consumed by `saymo auto`.
- Local control surface for speak, stop, auto-answer toggle, takeover, and
  optional safety actions.
- Expanded global hotkeys for approved-draft request, skip, capture marker,
  status, and hard-disable.
- Hotkey doctor diagnostics for listener, process, Accessibility permission,
  and effective bindings.
- Audit and regression checks for disabled auto-answer and manual takeover.

Archives:
- `.planning/milestones/v1.6-ROADMAP.md`
- `.planning/milestones/v1.6-REQUIREMENTS.md`
- `.planning/milestones/v1.6-MILESTONE-AUDIT.md`
- `.planning/milestones/v1.6-phases/`

### v1.5 Live Review + Safe Approved Speak

**Started:** 2026-05-21
**Completed:** 2026-05-21
**Archived:** 2026-05-21
**Status:** Complete

Focus: make the live loop reliable after real call recordings by improving
post-call review, handoff detection, speaker bootstrapping, approved draft
playback, and regression replay.

Delivered:
- Prioritized post-call review queue for handoffs, questions, mentions, and
  classifier-critical labels.
- Addressing v2 that separates direct handoffs from incidental name mentions
  and explains why Saymo answers, waits, or skips.
- Speaker bootstrap workflow to reduce `unknown` coverage without required
  live diarization.
- Safe playback of explicitly approved generated drafts through local
  TTS/playback gates.
- Saved-session regression replay with sanitized reliability reports.

Archives:
- `.planning/milestones/v1.5-ROADMAP.md`
- `.planning/milestones/v1.5-REQUIREMENTS.md`
- `.planning/milestones/v1.5-MILESTONE-AUDIT.md`
- `.planning/milestones/v1.5-phases/`

### v1.4 Live Conversation Memory + Answer Cockpit

**Started:** 2026-05-20
**Completed:** 2026-05-20
**Archived:** 2026-05-20
**Status:** Complete

Focus: turn recorded and live call context into local meeting memory plus an
explicit answer cockpit, so Saymo can show why it thinks the user was addressed,
draft a source-grounded answer, and wait for speak/edit/skip/takeover approval.

Delivered:
- Full-session local transcript ledgers and summaries for captured meetings.
- Local meeting search and cited `meeting-ask` over current or past sessions.
- Pending answer drafts grounded in meeting memory and configured source
  plugins.
- CLI/TUI-compatible answer cockpit with speak/edit/skip/takeover actions.
- Local JSONL audit trail and sanitized audit reports for trigger/draft/action
  evidence.

Archives:
- `.planning/milestones/v1.4-ROADMAP.md`
- `.planning/milestones/v1.4-REQUIREMENTS.md`
- `.planning/milestones/v1.4-MILESTONE-AUDIT.md`

### v1.3 Local Diarization Assist

**Started:** 2026-05-20
**Completed:** 2026-05-20
**Archived:** 2026-05-20
**Status:** Complete

Focus: make local speaker identity useful during trigger training by adding
optional diarization, speaker-cluster review, and safe promotion into existing
`me`/`other`/`unknown` labels.

Delivered:
- Optional local diarization backend detection and configuration.
- Session-level speaker suggestions stored as local sidecars.
- Review and promotion flow for diarization suggestions.
- Speaker-label quality reports before training/readiness uses suggestions.

Archives:
- `.planning/milestones/v1.3-ROADMAP.md`
- `.planning/milestones/v1.3-REQUIREMENTS.md`
- `.planning/milestones/v1.3-MILESTONE-AUDIT.md`

### v1.2 Trigger Training Console

**Started:** 2026-05-20
**Completed:** 2026-05-20
**Archived:** 2026-05-20
**Status:** Complete

Focus: turn recorded call samples into a practical local loop for session
review, relabeling, and safe classifier promotion.

Delivered:
- Named capture sessions with local ledgers, summaries, and profile/session
  inspection commands.
- CLI review/relabel workflow for sample category, speaker, and answer-decision
  labels.
- Sanitized session/category review reports for training data inspection.
- Readiness and holdout evaluation commands for the local trigger classifier.
- Guarded per-profile live-assist enablement that keeps deterministic
  trigger/addressing checks as the safety boundary.

Archives:
- `.planning/milestones/v1.2-ROADMAP.md`
- `.planning/milestones/v1.2-REQUIREMENTS.md`
- `.planning/milestones/v1.2-MILESTONE-AUDIT.md`

### v1.1 Call Intelligence Loop

**Started:** 2026-05-18
**Completed:** 2026-05-18
**Archived:** 2026-05-19
**Status:** Complete

Focus: make captured samples and provider probes explain speaker context,
learned trigger confidence, and provider-specific latency bottlenecks.

Delivered:
- Speaker-aware trigger samples and speaker-grouped evaluation.
- Accepted/rejected sample labels plus local classifier training.
- Separate `mentioned_me` vs `asked_to_speak` sample categories for plain name
  mentions and true floor handoffs.
- Classifier shadow diagnostics for `trigger-eval` and `trigger-check`.
- Provider latency probe with JSON/Markdown history by profile/provider.

### v1.0 Speedly Catcher + Speedly Sayer

**Started:** 2026-05-15
**Completed:** 2026-05-15
**Status:** Complete

Focus: make live-call trigger detection and prepared-response playback faster,
measurable, and easier to tune from captured meeting samples.

Delivered:
- Live latency metrics and configurable catcher tuning.
- Offline trigger sample evaluation with fuzzy variant promotion.
- Auto preflight diagnostics and structured playback blocked reasons.
- Trigger sample list/replay/report commands.

## Historical Baseline

Before GSD planning was introduced, Saymo already had a working local voice
assistant path: setup wizard, TTS engines, BlackHole routing, provider
automation, prepare/speak/auto commands, hotkeys, manual takeover, trigger
diagnostics, response cache preparation, and trigger sample capture.
