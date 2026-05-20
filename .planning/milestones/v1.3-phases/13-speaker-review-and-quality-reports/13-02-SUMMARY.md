# 13-02 Summary: Add Speaker Suggestion Apply/Reject Metadata

## Completed

- Extended sidecar suggestion records with `reviewed_speaker` and `reviewed_at`
  while preserving original `speaker_id` and `suggested_speaker`.
- Added pure helpers for finding and reviewing one sample suggestion.
- Added `trigger-samples speaker-suggestion` for show, accept, reject, and
  override workflows.
- Added prefixed interactive review actions: `suggest accept`,
  `suggest reject`, and `suggest other`.

## Files Changed

- `saymo/analysis/diarization.py`
- `saymo/analysis/trigger_review.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_diarization.py`
- `tests/analysis/test_trigger_review.py`
- `tests/test_trigger_check.py`

## Verification

- Focused CLI tests prove accept/override update sample JSON `speaker`, reject
  does not, and sidecar suggestion fields remain available for audit.
