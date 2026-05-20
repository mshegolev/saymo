# Phase 8 Verification

status: passed

## Evidence

- `.venv/bin/python -m pytest -q tests/analysis/test_trigger_capture.py tests/analysis/test_trigger_sessions.py tests/test_trigger_check.py`
  - 42 passed
- `.venv/bin/python -m pytest -q -k 'not qwen3_compute_loss'`
  - 259 passed, 6 deselected
- `.venv/bin/saymo -c config.yaml trigger-capture --help`
  - shows `--session`
- `.venv/bin/saymo -c config.yaml trigger-sessions --help`
  - lists `list` and `summary`
- `git diff --check`
  - passed

## Result

SES-01, SES-02, and SES-03 are complete. Capture runs now produce named local
session ledgers, every new saved sample can carry session metadata, and prior
sessions can be listed or summarized by profile.
