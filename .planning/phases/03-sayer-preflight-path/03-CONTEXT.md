# Phase 3 Context: Sayer Preflight Path

## Goal

Make prepared-response readiness explicit before calls and keep auto-mode
responsive when playback cannot start.

## Existing Baseline

- `saymo speak` and the auto hotkey could force prepared playback, but blocked
  paths were only printed ad hoc.
- There was no single command to check cache, devices, provider readiness,
  triggers, fallback, and tuning before joining a call.
- Response cache misses fell back to standup playback, but the reason was not
  surfaced as structured metadata.

## Decisions

- Make preflight a dry-run diagnostic command: `saymo auto-preflight`.
- Treat prepared standup, capture input, playback output, provider output,
  profile triggers, and provider tab as blocking checks.
- Treat response cache coverage and fallback mode as visible but non-blocking.

