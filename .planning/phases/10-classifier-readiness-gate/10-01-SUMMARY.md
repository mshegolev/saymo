# Plan 10-01 Summary: Classifier Readiness Metrics

## Completed

- Added dependency-free readiness helpers for accepted/rejected balance,
  category coverage, mention-vs-handoff coverage, ratios, and missing gates.
- Added `trigger-classifier readiness` with configurable minimum total and
  per-class thresholds.
- Added unit and CLI coverage for not-ready and ready datasets.

## Files

- `saymo/analysis/trigger_readiness.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_trigger_readiness.py`
- `tests/test_trigger_check.py`

## Verification

- `.venv/bin/python -m pytest -q tests/test_trigger_check.py tests/analysis/test_trigger_review.py tests/analysis/test_trigger_readiness.py`
  - 44 passed
