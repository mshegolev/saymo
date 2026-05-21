# Phase 22 Summary: Regression Replay

## Completed

- Added `saymo.analysis.regression_replay` metrics, JSON, and Markdown report
  contracts.
- Added `saymo trigger-sessions replay`.
- Added false handoff, missed handoff, question noise, speaker coverage, review
  coverage, and readiness metrics.
- Added sanitized JSON baseline comparison with deltas.
- Added report/JSON output that omits raw transcripts and audio.

## Verification

- `uv run pytest tests/analysis/test_regression_replay.py tests/test_trigger_check.py::test_trigger_sessions_replay_exports_sanitized_regression_report`

## Notes

- False handoffs and missed handoffs use reviewed `answer_decision` labels as
  ground truth when available.
- The command is safe to run on local captured sessions; it does not modify
  samples.

