status: passed

# Phase 13 Verification

## Goal-Backward Check

Phase 13 promised that users can inspect, accept, reject, override, and measure
speaker suggestions before they affect training.

## Evidence

- `trigger-samples speaker-suggestion` can show, accept, reject, or override a
  sample suggestion.
- `trigger-samples review` can show a matching sidecar suggestion and parse
  prefixed suggestion actions.
- Accepted and overridden suggestions update sample JSON `speaker`; rejected
  suggestions update only sidecar review metadata.
- Sidecar records preserve original `speaker_id` and `suggested_speaker` after
  review.
- `trigger-sessions speaker-report` exports sanitized speaker-review quality
  metrics with unknown coverage, accepted/rejected/overridden/pending counts,
  confidence buckets, and conflict rows.
- `trigger-eval` and classifier training ignore unreviewed sidecar suggestions
  because they read the authoritative sample JSON speaker field.

## Verification Commands

- `.venv/bin/python -m pytest -q tests/analysis/test_diarization.py tests/analysis/test_trigger_review.py tests/analysis/test_trigger_readiness.py tests/test_trigger_check.py`
  - Result: 64 passed in 0.63s.
- `.venv/bin/python -m pytest -q tests/analysis/test_diarization.py tests/analysis/test_trigger_review.py tests/analysis/test_trigger_readiness.py tests/analysis/test_trigger_classifier.py tests/analysis/test_trigger_sessions.py tests/test_config.py tests/test_trigger_check.py`
  - Result: 95 passed in 0.67s.
- `.venv/bin/python -m pytest -q`
  - Result: 304 passed in 3.07s.
- `.venv/bin/saymo trigger-samples speaker-suggestion --help`
  - Result: command help rendered.
- `.venv/bin/saymo trigger-sessions speaker-report --help`
  - Result: command help rendered.
- `git diff --check`
  - Result: no whitespace errors.

## Requirements

- SPKR-03: passed
- QUAL-01: passed
- QUAL-02: passed
- QUAL-03: passed
