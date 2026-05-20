# Plan 09-02 Summary: Category Relabel Command

## Completed

- Added category relabel planning/application helpers that validate target
  categories, update metadata, and move JSON plus adjacent WAV files when
  present.
- Added `trigger-samples category SAMPLE.json --category ...`.
- Preserved legacy JSON-only correction while keeping sample metadata
  discoverable under the corrected category folder.

## Files

- `saymo/analysis/trigger_review.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_trigger_review.py`
- `tests/test_trigger_check.py`

## Verification

- `.venv/bin/python -m pytest -q tests/test_trigger_check.py tests/analysis/test_trigger_review.py tests/analysis/test_trigger_readiness.py`
  - 50 passed
