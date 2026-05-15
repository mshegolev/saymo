# Milestones

## Current

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
