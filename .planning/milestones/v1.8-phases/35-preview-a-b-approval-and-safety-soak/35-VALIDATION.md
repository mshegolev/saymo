# Phase 35 Validation Strategy

**Created:** 2026-07-07

## Must Prove

- Approval requires a completed/scored score report.
- Approval requires 7/10 similarity, artifacts, and call-readiness scores or an
  explicit override reason.
- Rejection clears call approval.
- Preview audit is marked preview-only and does not store text or transcript.
- Safety soak fails on voice profile, metadata, and non-cloned live-call
  blockers.

## Automated Coverage

- Unit tests for approval/rejection and preview audit.
- CLI tests for approve/reject/preview dry-run.
- Safety-soak tests for voice readiness blocker rules.
