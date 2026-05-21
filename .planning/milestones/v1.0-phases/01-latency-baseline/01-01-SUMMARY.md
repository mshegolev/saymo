# Summary 01-01: Instrument Catch-Path Timings

## Completed

- Added `LiveConfig` and `resolve_live_tuning()` in `saymo/config.py`.
- Updated `saymo auto` to use live tuning for chunk length, overlap, read
  timeout, cooldown, silence threshold, and pre-speak delay.
- Added catch latency output for capture, STT, trigger match, addressing, and
  action decisions.

## Files

- `saymo/config.py`
- `saymo/commands/core.py`
- `tests/test_live_tuning_config.py`

