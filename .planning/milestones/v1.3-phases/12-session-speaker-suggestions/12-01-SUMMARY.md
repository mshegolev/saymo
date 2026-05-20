---
phase: 12-session-speaker-suggestions
plan: 01
subsystem: diarization
requirements-completed: [DIAR-04]
completed: 2026-05-20
---

# Plan 12-01 Summary: Load Session Audio Windows And Run Diarization Backend

## Completed

- Added session id resolution by exact/prefix match from ledgers or sample
  metadata.
- Added `trigger-sessions diarize` for one profile/session.
- Added deterministic `--segments-json` import path for tests and manual
  backend output.
- Added optional pyannote runner behind Phase 11 availability checks.

## Files

- `saymo/analysis/diarization.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_diarization.py`
- `tests/test_trigger_check.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_diarization.py tests/test_trigger_check.py`
  - 48 passed
