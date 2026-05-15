# Phase 1 Context: Latency Baseline

## Goal

Add timing visibility around the live call catcher and prepared playback path
without changing trigger gating behavior.

## Existing Baseline

- `saymo/commands/core.py::_auto` ran capture, STT, trigger detection,
  addressing, confirmation, response resolution, and playback with only a
  coarse `resolve/play/total` line.
- `_resolve_auto_response` returned only a path, so auto-mode could not report
  why a specific response path was selected.
- `_play_cached_audio` printed errors but returned no structured blocked reason.

## Decisions

- Keep all timing local and console-based; no persistent telemetry.
- Preserve `_resolve_auto_response` as a Path-returning compatibility wrapper.
- Add metadata/result objects only where they help diagnostics and tests.

