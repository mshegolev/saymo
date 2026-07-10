---
phase: 48-dry-run-orchestrator-and-result-contract
plan: 02
subsystem: cli
tags: [pytest, click, dry-run, launch-readiness, evidence]

# Dependency graph
requires:
  - phase: 48-dry-run-orchestrator-and-result-contract
    provides: RED dry-run CLI and launch-readiness helper contracts from Plan 48-01
provides:
  - "saymo dry-run Click command over launch readiness with prepare=False"
  - "Parameterized launch-readiness human label and artifact mode helpers"
  - "Dry-run JSON stdout contract with mode=dry-run and no artifact-only metadata"
affects: [48, 49, 50, 51, dry-run, call-ready, launch-readiness]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Thin Click command module registered through saymo.commands package import"
    - "Launch-readiness report reused for dry-run without new result model"
    - "Artifact mode parameter keeps flat launch-readiness evidence schema"

key-files:
  created:
    - saymo/commands/dry_run.py
  modified:
    - saymo/analysis/launch_readiness.py
    - saymo/commands/__init__.py

key-decisions:
  - "Reused LaunchReadinessReport and LaunchReadinessCheck for dry-run instead of adding a second result model."
  - "Kept dry-run read-only by hardcoding prepare=False and avoiding audio/provider/realtime/TTS mutation imports."
  - "Kept JSON stdout artifact-metadata-free while --output writes the flat launch-readiness artifact with mode=dry-run."

patterns-established:
  - "Operator dry-run commands can wrap collect_launch_readiness directly with prepare=False."
  - "Human launch-readiness labels are parameterized only at the top-level result line."
  - "Artifact-only metadata belongs in write_launch_readiness_artifact, not LaunchReadinessReport.to_dict()."

requirements-completed: [DRY-01, DRY-02, DRY-03]

# Metrics
duration: 3min
completed: 2026-07-10
---

# Phase 48 Plan 02: Dry-Run Command Summary

**Read-only `saymo dry-run` shell over launch readiness with dry-run output mode and preserved call-ready defaults**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-10T12:24:17Z
- **Completed:** 2026-07-10T12:26:50Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Parameterized `render_launch_readiness()` so `call-ready` remains the default while dry-run can render `dry-run: ready` or `dry-run: not ready`.
- Parameterized `write_launch_readiness_artifact()` so artifacts keep the flat launch-readiness schema and can write `mode: "dry-run"`.
- Added and registered `saymo dry-run` with `-p/--profile`, `--provider`, `--json`, and `--output`, with no `--prepare` option and readiness-based exit codes.
- Verified the 48-01 RED tests now pass without weakening them, and the existing call-ready/realtime targeted tests remain green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Parameterize launch-readiness rendering and artifact mode** - `839d3e8` (feat)
2. **Task 2: Add and register the `saymo dry-run` command** - `46a80d0` (feat)

## Files Created/Modified

- `saymo/analysis/launch_readiness.py` - Added keyword-only `label` and `mode` parameters while preserving default call-ready output and artifact metadata.
- `saymo/commands/dry_run.py` - New read-only dry-run Click command that collects readiness with `prepare=False`, emits sanitized human/JSON output, and optionally writes an artifact.
- `saymo/commands/__init__.py` - Registered the dry-run command module with the existing command import pattern.

## Decisions Made

- Reused the existing launch-readiness model and collector instead of introducing a dry-run-specific report type.
- Kept dry-run JSON stdout to `report.to_dict()` plus `mode`, excluding artifact-only keys such as `artifact_path`, `schema_version`, `evidence_kind`, and `created_at`.
- Kept dry-run implementation isolated from audio, provider, realtime, synthesis, training, download, cache deletion, and protected asset mutation paths.

## Verification

- `uv run pytest tests/analysis/test_launch_readiness.py::test_render_and_artifact_support_dry_run_mode_without_breaking_call_ready tests/analysis/test_launch_readiness.py::test_write_launch_readiness_artifact_adds_phase40_metadata_without_wrapping -q` - 2 passed.
- `uv run pytest tests/test_dry_run_cli.py tests/test_call_ready_cli.py tests/analysis/test_launch_readiness.py::test_render_and_artifact_support_dry_run_mode_without_breaking_call_ready tests/analysis/test_realtime_gate.py -q` - 26 passed.
- `uv run pytest tests/test_dry_run_cli.py tests/test_call_ready_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_realtime_gate.py -q` - 41 passed.
- `uv run pytest` - 624 passed.
- Static acceptance checks confirmed dry-run registration, no `--prepare`, no forbidden audio/provider/realtime/TTS/cache mutation references, and no hardcoded call-ready writer mode assignment.

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 49 can build on the dry-run shell and launch-readiness artifact mode to add source, prepared-audio, cache, and voice readiness depth. The command remains read-only and does not start realtime mode or mutate audio/provider assets.

---
*Phase: 48-dry-run-orchestrator-and-result-contract*
*Completed: 2026-07-10*

## Self-Check: PASSED

- Found `saymo/commands/dry_run.py`.
- Found `saymo/analysis/launch_readiness.py`.
- Found `saymo/commands/__init__.py`.
- Found `.planning/phases/48-dry-run-orchestrator-and-result-contract/48-02-SUMMARY.md`.
- Found commit `839d3e8`.
- Found commit `46a80d0`.
