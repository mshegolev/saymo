# 13-01 Summary: Extend Sample Review With Speaker Suggestions

## Completed

- `trigger-samples replay` and `trigger-samples review` now show a matching
  session speaker suggestion when a diarization sidecar exists.
- Missing sidecars remain non-blocking, so legacy samples keep reviewing
  normally.
- Suggestion display includes speaker id, mapped label, review status,
  confidence, reviewed label, and current sample speaker.

## Files Changed

- `saymo/commands/tests.py`
- `tests/test_trigger_check.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_diarization.py tests/analysis/test_trigger_review.py tests/analysis/test_trigger_readiness.py tests/test_trigger_check.py`
- Result: 64 passed.
