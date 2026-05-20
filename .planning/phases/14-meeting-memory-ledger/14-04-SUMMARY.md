# 14-04 Summary: Session Summary Rendering And Tests

## Completed

- Added meeting summary aggregation for questions, handoffs, action-item-like
  statements, speakers, categories, and incomplete transcript coverage.
- Added `saymo meeting-summary` with optional `--build-missing` and markdown
  output.
- Existing trigger-session commands remain unchanged.

## Files Changed

- `saymo/analysis/meeting_memory.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_meeting_memory.py`
- `tests/test_meeting_memory_cli.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_meeting_memory.py tests/test_meeting_memory_cli.py tests/test_config.py`
  - 28 passed
