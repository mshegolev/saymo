# 14-03 Summary: Retention Config And Local Path Diagnostics

## Completed

- Added `meeting_memory.enabled`, `retain_transcripts`, `base_dir`,
  `default_window_seconds`, and `summary_max_items` config fields.
- Added `saymo meeting-memory build` with base-dir, ledger path, retention, and
  segment diagnostics.
- Supported `--retain/--no-retain` per build.

## Files Changed

- `saymo/config.py`
- `config.example.yaml`
- `saymo/commands/tests.py`
- `tests/test_config.py`
- `tests/test_meeting_memory_cli.py`

## Verification

- `.venv/bin/python -m pytest -q tests/analysis/test_meeting_memory.py tests/test_meeting_memory_cli.py tests/test_config.py`
  - 28 passed
