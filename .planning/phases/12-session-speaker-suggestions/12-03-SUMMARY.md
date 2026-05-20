---
phase: 12-session-speaker-suggestions
plan: 03
subsystem: diarization
requirements-completed: [SPKR-01, SPKR-02]
completed: 2026-05-20
---

# Plan 12-03 Summary: Session Speaker Summary Command Output

## Completed

- Added `trigger-sessions speakers` for speaker-cluster summaries, unresolved
  suggestions, unknown samples, time ranges, confidence, and mapped labels.
- Added `trigger-sessions map-speaker` for session-local mapping from
  diarization speaker ids to `me`, `other`, or `unknown`.
- Mapping updates sidecar suggestions only; sample speaker metadata remains
  untouched.
- Documented new session diarization commands.

## Files

- `saymo/analysis/diarization.py`
- `saymo/commands/tests.py`
- `docs/PRD.md`
- `docs/QUICK-START.md`
- `tests/analysis/test_diarization.py`
- `tests/test_trigger_check.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_diarization.py tests/test_trigger_check.py`
  - 48 passed
