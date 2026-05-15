# Summary 03-01: Live-Call Preflight Command

## Completed

- Added `saymo auto-preflight`.
- The command checks prepared audio, devices, provider tab, profile triggers,
  response-cache coverage, fallback mode, and live tuning.
- Response cache coverage is visible but non-blocking so missing optional Q&A
  variants do not block prepared standup playback.

## Tests

- `test_auto_preflight_reports_ready_with_nonblocking_cache_warning`

