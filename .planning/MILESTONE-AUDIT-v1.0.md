# Milestone Audit: v1.0 Speedly Catcher + Speedly Sayer

status: passed

## Scope

Milestone v1.0 targeted faster, more measurable live-call trigger detection and
prepared-response playback, plus a local sample review loop.

## Requirement Coverage

- CATCH-01: catch-path latency is printed from `saymo auto`.
- CATCH-02: live tuning is configurable globally and per meeting profile.
- CATCH-03: `saymo trigger-eval` evaluates saved samples.
- CATCH-04: `saymo trigger-eval --promote` learns a variant and re-runs.
- SAY-01: `saymo auto-preflight` checks readiness before a call.
- SAY-02: auto-mode prints playback-start latency.
- SAY-03: forced playback returns structured blocked reasons.
- SAY-04: cache misses route to prepared standup fallback by default.
- TRAIN-01: `saymo trigger-samples list` inspects sample metadata.
- TRAIN-02: `saymo trigger-samples replay` reclassifies and optionally plays.
- TRAIN-03: `saymo trigger-samples report` exports sanitized markdown.

## Verification

- `.venv/bin/python -m pytest -q`
  - 241 passed
- `git diff --check`
  - passed
- `.venv/bin/saymo --help`
  - command surface includes new CLI commands

## Residual Notes

The evaluator becomes more valuable as real call samples accumulate under
`~/.saymo/trigger_samples/<profile>/`.

