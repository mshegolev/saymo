# Plan 10-02 Summary: Holdout Evaluation Reporting

## Completed

- Added deterministic labeled train/holdout splitting for local classifier
  samples.
- Added holdout evaluation with confusion matrix, precision, recall, accuracy,
  and train/holdout counts.
- Added `trigger-classifier evaluate` and CLI coverage for the reported metrics.

## Files

- `saymo/analysis/trigger_readiness.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_trigger_readiness.py`
- `tests/test_trigger_check.py`

## Verification

- `.venv/bin/python -m pytest -q tests/test_trigger_check.py tests/analysis/test_trigger_review.py tests/analysis/test_trigger_readiness.py`
  - 44 passed
