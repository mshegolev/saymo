# 17-02 Summary: Speak/Edit/Skip/Takeover Action Handling

## Completed

- Added explicit cockpit actions: speak, edit, skip, and takeover.
- `speak` records approval while leaving `playback_started=false`.
- `edit` stores approved edited text.
- `skip` and `takeover` are persisted as normal outcomes.
- Added `saymo answer-cockpit action`.

## Files Changed

- `saymo/analysis/answer_cockpit.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_answer_cockpit.py`
- `tests/test_meeting_memory_cli.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_answer_cockpit.py tests/analysis/test_meeting_memory.py tests/test_meeting_memory_cli.py`
  - 22 passed
