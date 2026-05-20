---
phase: 11-diarization-adapter-and-config
plan: 01
subsystem: diarization
requirements-completed: [DIAR-01, DIAR-02, DIAR-03]
completed: 2026-05-20
---

# Plan 11-01 Summary: Diarization Config And Availability Checks

## Completed

- Added `DiarizationConfig` to the main Saymo config dataclass.
- Added normalized config view and availability diagnostics for disabled,
  unsupported, missing token, missing dependency, and ready states.
- Kept pyannote as an optional backend checked only through runtime helpers.
- Added tests for default-disabled, token-env, ready, and normalization paths.

## Files

- `saymo/config.py`
- `saymo/analysis/diarization.py`
- `tests/test_config.py`
- `tests/analysis/test_diarization.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_diarization.py tests/test_config.py tests/test_trigger_check.py`
  - 65 passed
