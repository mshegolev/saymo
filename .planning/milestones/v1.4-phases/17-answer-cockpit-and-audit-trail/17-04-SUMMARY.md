# 17-04 Summary: Sanitized Replay/Report Flow And Safety Tests

## Completed

- Added `saymo answer-audit list` and `saymo answer-audit report`.
- Sanitized reports omit raw audio, secrets, and config values.
- Added tests proving speak action records approval without automatic playback.
- Updated quick-start and PRD command references.

## Files Changed

- `saymo/analysis/answer_cockpit.py`
- `saymo/commands/tests.py`
- `docs/QUICK-START.md`
- `docs/PRD.md`
- `tests/analysis/test_answer_cockpit.py`
- `tests/test_meeting_memory_cli.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_answer_cockpit.py tests/analysis/test_meeting_memory.py tests/test_meeting_memory_cli.py`
  - 22 passed
