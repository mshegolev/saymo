# Summary 06-01: Accepted/Rejected Sample Labels

## Completed

- Added `answer_decision` loading with legacy default `unlabeled`.
- Added `trigger-samples decision` to write `accepted`, `rejected`, or
  `unlabeled` into one sample JSON file.
- Included answer-decision labels in sample list, replay, and sanitized report
  output.

## Files

- `saymo/commands/tests.py`
- `tests/test_trigger_check.py`
