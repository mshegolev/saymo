# 16-01 Summary: Answer Draft Contracts With Evidence And Citations

## Completed

- Added answer draft, trigger evidence, source evidence, and citation
  dataclasses in `saymo.analysis.answer_cockpit`.
- Added JSON serialization/deserialization plus draft JSON write/load helpers.
- Added confidence calculation that separates trigger evidence from meeting
  citations and source availability.

## Files Changed

- `saymo/analysis/answer_cockpit.py`
- `tests/analysis/test_answer_cockpit.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_answer_cockpit.py tests/analysis/test_meeting_memory.py tests/test_meeting_memory_cli.py`
  - 16 passed
