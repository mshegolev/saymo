---
phase: 12-session-speaker-suggestions
plan: 02
subsystem: diarization
requirements-completed: [DIAR-04, SPKR-01]
completed: 2026-05-20
---

# Plan 12-02 Summary: Store Diarization Sidecars And Sample Suggestions

## Completed

- Added `.diarization.json` sidecars under the existing profile `_sessions`
  directory.
- Added per-sample speaker suggestions matched by session sequence/window
  overlap.
- Suggestions preserve current manual `speaker` labels and do not mutate sample
  JSON.
- Session listing now ignores `.diarization.json` sidecars when loading ledgers.

## Files

- `saymo/analysis/diarization.py`
- `saymo/analysis/trigger_sessions.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_diarization.py`
- `tests/test_trigger_check.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_diarization.py tests/test_trigger_check.py`
  - 48 passed
