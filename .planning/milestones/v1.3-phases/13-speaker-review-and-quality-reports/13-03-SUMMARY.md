# 13-03 Summary: Add Speaker Quality And Conflict Reports

## Completed

- Added speaker-quality report metrics for unknown coverage, review status
  counts, confidence buckets, and manual-vs-suggested conflicts.
- Added `trigger-sessions speaker-report` with optional markdown export.
- Rendered reports include aggregate metadata and sample filenames only; they
  omit transcript text, raw audio, and private config values.

## Files Changed

- `saymo/analysis/diarization.py`
- `saymo/commands/tests.py`
- `docs/PRD.md`
- `docs/QUICK-START.md`
- `tests/analysis/test_diarization.py`
- `tests/test_trigger_check.py`

## Verification

- Report tests verify accepted/rejected counts, unknown coverage, confidence
  buckets, conflict rows, and transcript omission.
