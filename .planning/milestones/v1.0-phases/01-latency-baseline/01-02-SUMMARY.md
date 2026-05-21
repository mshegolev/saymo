# Summary 01-02: Instrument Say-Path Playback Timings

## Completed

- Added `AutoResponseDecision` and `PlaybackResult`.
- Kept `_resolve_auto_response()` backward-compatible while adding
  `_resolve_auto_response_decision()` for auto-mode diagnostics.
- `_play_cached_audio()` now returns blocked reasons for missing files, missing
  BlackHole output, and missing provider tabs.
- `saymo auto` now prints response route, playback-start latency, play duration,
  total latency, and blocked reason when playback cannot start.

## Files

- `saymo/commands/__init__.py`
- `saymo/commands/core.py`
- `saymo/cli.py`
- `tests/test_auto_qa_flow.py`
- `tests/test_playback_fallback.py`

