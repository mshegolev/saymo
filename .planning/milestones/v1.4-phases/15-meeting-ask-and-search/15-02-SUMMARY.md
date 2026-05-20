# 15-02 Summary: Cited Meeting Ask Command And Retrieval

## Completed

- Added deterministic meeting ask retrieval over local transcript evidence.
- Added answer rendering with session/segment/timestamp citations.
- Added no-evidence diagnostics that avoid unsupported claims.
- Added `saymo meeting-ask`.

## Files Changed

- `saymo/analysis/meeting_memory.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_meeting_memory.py`
- `tests/test_meeting_memory_cli.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_meeting_memory.py tests/test_meeting_memory_cli.py`
  - 11 passed
