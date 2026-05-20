# Summary 05-01: Speaker Label Metadata Support

## Completed

- Added `speaker` metadata to new trigger-capture samples, defaulting to
  `unknown`.
- Legacy sample JSON without `speaker` now loads as `unknown`.
- `trigger-samples list`, `replay`, and `report` show speaker labels.

## Files

- `saymo/analysis/trigger_capture.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_trigger_capture.py`
- `tests/test_trigger_check.py`

