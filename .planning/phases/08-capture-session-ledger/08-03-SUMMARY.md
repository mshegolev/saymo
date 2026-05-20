# Plan 08-03 Summary: Session Commands And Docs

## Completed

- Added `saymo trigger-sessions list` for prior session rows by profile.
- Added `saymo trigger-sessions summary --session <id>` for per-meeting
  category, speaker, answer-decision, skipped-silence, and readiness counts.
- Updated `trigger-samples list` to show a sample's session id when present and
  to ignore `_sessions` ledger files.
- Documented the session workflow in `docs/QUICK-START.md`.

## Files

- `saymo/commands/tests.py`
- `tests/test_trigger_check.py`
- `docs/QUICK-START.md`

## Verification

- `.venv/bin/saymo -c config.yaml trigger-sessions --help`
  - lists `list` and `summary`
- `.venv/bin/python -m pytest -q tests/analysis/test_trigger_capture.py tests/analysis/test_trigger_sessions.py tests/test_trigger_check.py`
  - 42 passed
