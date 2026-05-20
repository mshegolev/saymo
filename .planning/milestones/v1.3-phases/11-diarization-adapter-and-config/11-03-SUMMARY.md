---
phase: 11-diarization-adapter-and-config
plan: 03
subsystem: diarization
requirements-completed: [DIAR-01, DIAR-02, DIAR-03]
completed: 2026-05-20
---

# Plan 11-03 Summary: CLI Diagnostics And Optional Setup Docs

## Completed

- Added `saymo diarization-check` with engine/model/device/token-env overrides.
- Diagnostics print disabled, availability, model, device, token env presence,
  missing components, and reason without exposing token values.
- Documented optional diarization config and CLI usage in public docs and the
  example config.
- Added CLI tests for disabled and missing-token output.

## Files

- `saymo/commands/tests.py`
- `config.example.yaml`
- `docs/PRD.md`
- `docs/QUICK-START.md`
- `tests/test_trigger_check.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_diarization.py tests/test_config.py tests/test_trigger_check.py`
  - 65 passed
