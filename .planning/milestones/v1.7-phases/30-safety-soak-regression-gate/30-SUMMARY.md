# Phase 30 Summary: Safety Soak Regression Gate

**Status:** complete
**Completed:** 2026-07-07

## What Shipped

- Added `saymo.analysis.safety_soak`, a sanitized aggregate safety gate over
  saved rehearsal artifacts and saved session-scorecard JSON.
- Added `saymo safety-soak` with repeated `--rehearsal` and
  `--scorecard-json` inputs, `--baseline-json` drift comparison, and optional
  Markdown/JSON exports.
- Added safety invariants for would-speak while auto-answer is off, manual
  takeover is active, hard-disable is active, or the playback gate reports an
  unapproved draft.
- Added baseline drift comparison for false handoffs, missed handoffs, question
  noise, unknown speakers, and max latency.
- Added unsafe automatic playback evidence for real-session scorecard JSON, so
  safety-soak can fail a real-session gate even when the scorecard has no
  rehearsal `would_speak` decision.
- Added safety-soak remediation hints and runnable scorecard rerun paths for
  rehearsal artifacts.
- Sanitized rehearsal JSON exports by omitting raw transcript text and volatile
  live-control fields such as `last_trigger`.
- Updated README and Quick Start with pre-call and pre-merge soak examples.

## Files Changed

- `saymo/analysis/safety_soak.py`
- `saymo/analysis/session_scorecard.py`
- `saymo/analysis/rehearsal.py`
- `saymo/analysis/remediation.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_rehearsal.py`
- `tests/analysis/test_safety_soak.py`
- `tests/analysis/test_session_scorecard.py`
- `tests/test_safety_soak_cli.py`
- `README.md`
- `docs/QUICK-START.md`

## Verification

- `uv run pytest tests/analysis/test_rehearsal.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py`
- `uv run pytest tests/analysis/test_session_scorecard.py tests/test_session_scorecard_cli.py tests/test_rehearsal_cli.py tests/test_hotkey_doctor.py tests/test_takeover_check.py`
- `uv run pytest`
