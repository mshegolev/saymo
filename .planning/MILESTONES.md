# Milestones

## Current

No active milestone.

Next step: run `$gsd-new-milestone` to define the next milestone.

## Completed

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
