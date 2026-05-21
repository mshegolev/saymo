# Phase 20 Summary: Speaker Bootstrap

## Completed

- Added `saymo trigger-sessions speaker-bootstrap`.
- Supported manual session-scoped bulk labeling with preview/apply behavior.
- Supported reviewed diarization suggestions as a bulk source.
- Preserved manual labels by default and added `--overwrite-manual` for
  explicit replacement.
- Stored `speaker_bootstrap` audit metadata on updated samples.
- Reported speaker counts, unknown speaker coverage, and readiness blockers
  after preview/apply.

## Verification

- `uv run pytest tests/test_trigger_check.py`

## Notes

- Manual mode works without diarization configured or available.
- Suggestions mode requires an existing diarization sidecar and only applies
  accepted/overridden reviewed suggestions.

