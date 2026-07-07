# Phase 32 Validation Strategy

**Created:** 2026-07-07

## Must Prove

- Every benchmark run writes `manifest.json`, `blind-review.md`, `review.json`,
  and `score-report.md`.
- Partial/interrupted runs keep useful evidence but are not approved.
- Unscored reports are not promotion-ready.
- Transcript text does not leak into new artifacts.
- Existing script CLI/tests remain compatible.

## Automated Coverage

- Unit tests for artifact helpers.
- Script tests for dry-run and interrupted output.
- Full pytest suite after integration.
