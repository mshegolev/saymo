---
phase: 48-dry-run-orchestrator-and-result-contract
plan: 01
subsystem: testing
tags: [pytest, click, tdd, dry-run, launch-readiness]

# Dependency graph
requires:
  - phase: 47-f5-prosody-metrics
    provides: Existing call-ready, readiness, and sanitized launch evidence contracts
provides:
  - RED CLI contract tests for the future saymo dry-run command
  - RED helper contract test for dry-run render label and artifact mode parameters
  - Static non-destructive guard for the future dry-run command module
affects: [48-02, dry-run, call-ready, launch-readiness]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Click CliRunner RED command contract tests
    - Launch-readiness sanitized JSON and artifact contract assertions
    - Source-free RED TDD plan execution

key-files:
  created:
    - tests/test_dry_run_cli.py
  modified:
    - tests/analysis/test_launch_readiness.py

key-decisions:
  - "Kept Plan 01 source-free: added RED tests only and left dry-run implementation for Plan 02."
  - "Did not invoke test-tts or any audio/provider paths; verification used pytest and static text checks only."
  - "Did not mark DRY requirements complete because this RED plan defines contracts but does not implement them."

patterns-established:
  - "Dry-run CLI tests monkeypatch saymo.commands.dry_run.collect_launch_readiness and require prepare=False."
  - "Dry-run JSON stdout must include mode=dry-run while excluding artifact-only metadata."
  - "Launch-readiness helper defaults must keep call-ready behavior while accepting dry-run label/mode overrides."

requirements-completed: []
requirements-covered-by-red-tests: [DRY-01, DRY-02, DRY-03]

# Metrics
duration: 4min
completed: 2026-07-10
---

# Phase 48 Plan 01: RED Dry-Run Contract Summary

**RED pytest contracts for the future `saymo dry-run` command, sanitized output/artifact mode, and non-destructive boundaries**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-10T12:15:22Z
- **Completed:** 2026-07-10T12:19:16Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `tests/test_dry_run_cli.py` with the required dry-run CLI, JSON, artifact, no-prepare, and non-destructive RED contract tests.
- Added `test_render_and_artifact_support_dry_run_mode_without_breaking_call_ready` to lock helper parameterization for Plan 02.
- Verified the new tests fail RED for missing dry-run module/registration and unsupported helper keywords, while existing call-ready sanity tests still pass.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add RED dry-run CLI contract tests** - `00e2d83` (test)
2. **Task 2: Add RED render and artifact helper parameterization tests** - `cce929f` (test)

## Files Created/Modified

- `tests/test_dry_run_cli.py` - New RED CLI contract tests for dry-run registration, readiness collection with `prepare=False`, output, JSON, artifacts, no `--prepare`, and static safety boundaries.
- `tests/analysis/test_launch_readiness.py` - New RED helper contract for `render_launch_readiness(label="dry-run")` and `write_launch_readiness_artifact(mode="dry-run")` while preserving call-ready defaults.

## Decisions Made

- Kept execution strictly source-free to honor the RED plan and critical constraint that implementation does not exist yet.
- Treated DRY-01, DRY-02, and DRY-03 as covered by RED tests but not completed requirements.
- Used only pytest, ripgrep, git, and planning-file updates; no TTS, audio playback, synthesis, model, cache, provider, or `.saymo` asset actions were run.

## Verification

- `uv run pytest tests/test_dry_run_cli.py -q` - RED as expected: 8 failures caused by missing `saymo.commands.dry_run` and missing `dry-run` registration.
- `uv run pytest tests/analysis/test_launch_readiness.py::test_render_and_artifact_support_dry_run_mode_without_breaking_call_ready -q` - RED as expected: `TypeError` for unsupported `label=` keyword.
- `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py::test_render_and_artifact_support_dry_run_mode_without_breaking_call_ready -q` - RED as expected: 9 failures from the same intended missing implementation/helper hooks.
- `uv run pytest tests/test_call_ready_cli.py::test_call_ready_prints_top_level_result tests/test_call_ready_cli.py::test_call_ready_json_is_sanitized -q` - passed, 2 tests.
- `rg -n "test-tts|saymo test-tts|sd\\.play|sd\\.rec|AudioCapture\\(" tests/test_dry_run_cli.py` - no matches.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The failing tests are intentional RED outcomes for Plan 02.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 02 can now implement the minimal dry-run command, register it, and parameterize launch-readiness render/artifact helpers against concrete failing tests.

## Self-Check: PASSED

- Found `tests/test_dry_run_cli.py`.
- Found `tests/analysis/test_launch_readiness.py`.
- Found `.planning/phases/48-dry-run-orchestrator-and-result-contract/48-01-SUMMARY.md`.
- Found commit `00e2d83`.
- Found commit `cce929f`.

---
*Phase: 48-dry-run-orchestrator-and-result-contract*
*Completed: 2026-07-10*
