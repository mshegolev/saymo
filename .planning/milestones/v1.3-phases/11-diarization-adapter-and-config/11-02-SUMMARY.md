---
phase: 11-diarization-adapter-and-config
plan: 02
subsystem: diarization
requirements-completed: [DIAR-01, DIAR-03]
completed: 2026-05-20
---

# Plan 11-02 Summary: Backend-Neutral Diarization Result Contracts

## Completed

- Added backend-neutral dataclasses for diarization availability, segments, and
  session results.
- Added JSON serialization/deserialization helpers for future session sidecars.
- Kept optional backend import detection behind helper functions so normal
  imports do not require diarization packages.

## Files

- `saymo/analysis/diarization.py`
- `tests/analysis/test_diarization.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_diarization.py tests/test_config.py tests/test_trigger_check.py`
  - 65 passed
