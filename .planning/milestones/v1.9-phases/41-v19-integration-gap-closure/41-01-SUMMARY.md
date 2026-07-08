---
phase: 41-v19-integration-gap-closure
plan: 41-01
status: complete
completed: 2026-07-08
requirements: [LAUN-04, LAUN-07, REAL-01, EVID-02, EVID-03]
key_files:
  - saymo/commands/core.py
  - tests/test_auto_qa_flow.py
  - tests/analysis/test_launch_readiness.py
commits:
  - 68c233c
  - a431f00
---

# Phase 41 Plan 01: v1.9 Integration Gap Closure Summary

Closed the two v1.9 integration audit blockers.

## What Changed

- `saymo prepare -p standup --save` now writes prepared-audio sidecar `source_sha256` from the saved Obsidian daily note hash, matching the hash later checked by call-ready prepared-audio freshness.
- `saymo auto` now emits sanitized realtime lifecycle and playback evidence through `RealtimeDecisionEvent`: `launch-start`, `launch-end`, `playback-attempted`, `stop-requested`, `cancel-playback`, and `playback-timeout`.
- Existing realtime decision tests now account for lifecycle rows without weakening cache, provider, addressing, or live-assist assertions.

## Verification

- RED: focused regression command failed before implementation with 5 failures covering missing lifecycle/playback/stop labels and the source hash mismatch.
- `uv run pytest tests/test_auto_qa_flow.py tests/analysis/test_launch_readiness.py tests/analysis/test_cache_metadata.py -q`
- `uv run pytest tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/test_session_scorecard_cli.py -q`
- `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py tests/test_realtime_static_guards.py -q`
- Phase 40 focused suite from `40-VALIDATION.md`
- `uv run pytest`
- Phase 40 static privacy guard
- Phase 40 static provider/audio mutation guard
- `git diff --check`

## Residual Risk

Automated checks cover the integration contract. Remaining risk is live macOS smoke only: real provider tab/mute state, BlackHole routing, Accessibility permissions, LaunchAgent state, and actual call audio timing.
