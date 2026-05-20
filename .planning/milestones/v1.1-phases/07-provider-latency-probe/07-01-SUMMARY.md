# Summary 07-01: Provider Latency Probe Command

## Completed

- Added `saymo provider-latency`.
- Resolved provider from the selected meeting profile with `--provider`
  override support.
- Added `--text`, `--audio`, `--output-dir`, `--device`, and timing flags for
  deterministic tests and live-call probing.
- Added blocked provider-tab reporting.

## Files

- `saymo/commands/tests.py`
- `tests/test_provider_latency.py`
