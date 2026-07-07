# Phase 30 Verification

**Verified:** 2026-07-07

## Commands

```bash
uv run pytest tests/analysis/test_rehearsal.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py
```

Result: `14 passed in 0.17s`

```bash
uv run pytest tests/analysis/test_session_scorecard.py tests/test_session_scorecard_cli.py tests/test_rehearsal_cli.py tests/test_hotkey_doctor.py tests/test_takeover_check.py
```

Result: `10 passed in 0.32s`

```bash
uv run pytest
```

Result: `380 passed, 1 skipped in 3.10s`

```bash
uv run saymo safety-soak --help
```

Result: command exits `0` and lists `--rehearsal`, `--scorecard-json`,
`--baseline-json`, `--output`, and `--json-output`.

## Notes

- Safety soak JSON and Markdown are derived from sanitized scorecards and do
  not include raw transcript text, raw audio, or local trigger content.
- Gate failures exit nonzero so the command can be used before merge or before
  trusting auto-answer in a live call.
- Integration review gaps closed after first pass: real-session unsafe
  automatic playback now fails the gate, safety-soak prints remediation hints,
  session-scorecard rehearsal rerun commands use the original artifact path,
  and rehearsal JSON export strips raw transcript plus volatile live-control
  trigger text.
