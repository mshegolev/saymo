# Phase 35 Context: Preview, A/B Approval, and Safety Soak

**Created:** 2026-07-07

## Goal

Prove that cloned voice output is previewed, approved, and covered by the same
pre-call safety gates before it reaches a real call.

## Findings

- Voice profile manifests already store approval state but no approval command
  exists yet.
- Phase 34 selector blocks live-call output when a profile is missing,
  unapproved, non-cloned, or cache metadata is stale.
- `auto-preflight` now exposes voice selector state.
- `safety_soak` currently detects handbrake and unapproved draft hazards from
  scorecard playback gate text; it can be extended to detect voice readiness
  blocker text.

## Implementation Boundary

- Add explicit profile approval/rejection commands linked to score reports.
- Add preview audit metadata without storing preview text.
- Extend safety-soak voice readiness violations.
- Do not auto-approve profiles, install packages, download models, train, or
  delete local assets.
