---
phase: 08-capture-session-ledger
plan: 02
subsystem: trigger-training
requirements-completed: [SES-01, SES-02]
completed: 2026-05-20
---

# Plan 08-02 Summary: Trigger Capture Session Wiring

## Completed

- Added `--session` to `saymo trigger-capture`.
- `trigger-capture` now starts a ledger before recording, writes the generated
  session id into every saved sample, counts skipped silence windows, and
  finalizes the ledger on normal completion, Ctrl+C, or failure.
- Capture output now prints the session id at start and a final local summary
  with windows, category, speaker, decision, readiness, and ledger path.

## Files

- `saymo/commands/tests.py`
- `tests/test_trigger_check.py`

## Verification

- `.venv/bin/saymo -c config.yaml trigger-capture --help`
  - shows `--session`
- `.venv/bin/python -m pytest -q tests/analysis/test_trigger_capture.py tests/analysis/test_trigger_sessions.py tests/test_trigger_check.py`
  - 42 passed
