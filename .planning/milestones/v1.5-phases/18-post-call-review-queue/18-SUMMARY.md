# Phase 18 Summary: Post-call Review Queue

## Completed

- Added reusable post-call queue scoring in `saymo.analysis.trigger_review`.
- Added review progress metrics with speaker, decision, category, and readiness
  blockers.
- Added `saymo trigger-samples queue` for prioritized session review previews.
- Added `saymo trigger-samples progress` for session-scoped review coverage.
- Kept existing `trigger-samples review/category/label/decision` commands as
  the metadata application path.

## Verification

- `uv run pytest tests/analysis/test_trigger_review.py tests/test_trigger_check.py`

## Notes

- Priority scoring treats behavioral disagreements as high value while avoiding
  noisy addressing-reason-only drift.
- Queue output includes the sample filename, full path, reasons, stored labels,
  current category, and local transcript for review.
- Progress output reports classifier readiness blockers without exporting raw
  audio or committing local samples.

