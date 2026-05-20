# 15-03 Summary: Sanitized Summary Export And Diagnostics

## Completed

- Added sanitized meeting export rendering.
- Sanitized output omits raw audio names, source sample paths, secrets, and
  config values.
- Extended `meeting-summary` with `--sanitized` and `--output`.
- Missing ledgers can be built explicitly with `--build-missing`.

## Files Changed

- `saymo/analysis/meeting_memory.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_meeting_memory.py`
- `tests/test_meeting_memory_cli.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_meeting_memory.py tests/test_meeting_memory_cli.py`
  - 11 passed
