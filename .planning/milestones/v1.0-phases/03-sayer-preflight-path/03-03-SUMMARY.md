# Summary 03-03: Cache-Miss Fallback Behavior

## Completed

- Added `_resolve_auto_response_decision()` while preserving
  `_resolve_auto_response()`.
- Auto-mode now prints response route metadata before playback.
- Live fallback errors return a standup fallback decision.

## Tests

- Existing response-resolution tests.
- `test_response_decision_reports_cache_reason`

