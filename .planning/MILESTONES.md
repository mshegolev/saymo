# Milestones

## Current

No active milestone. Start the next cycle with `$gsd-new-milestone`.

## Completed

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
