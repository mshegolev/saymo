# Phase 21 Summary: Approved Draft Playback

## Completed

- Added `ApprovedPlaybackResult` and `approved_playback_event`.
- Wired `answer-cockpit action --action speak` into local TTS/playback by
  default after approval.
- Added `--no-playback`, `--preview`, `--monitor/--no-monitor`, `--timeout`,
  and `--max-duration`.
- Added blocked-reason gates for empty approved text and excessive estimated
  speech duration before synthesis.
- Appended `approved_playback` audit events with TTS engine, output route,
  monitor route, timing, preview, timeout, max-duration, and blocked reason.

## Verification

- `uv run pytest tests/analysis/test_answer_cockpit.py tests/test_trigger_check.py`

## Notes

- The pure state transition still records approval; actual audio routing is
  performed only by the explicit CLI caller.
- Preview mode uses the monitor device when configured, otherwise the normal
  playback device.

