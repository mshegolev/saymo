---
phase: 49-source-prepared-audio-cache-and-voice-readiness
plan: "01"
subsystem: testing
tags: [pytest, dry-run, launch-readiness, response-cache, voice-metadata]

requires:
  - phase: 48-dry-run-orchestrator-and-result-contract
    provides: Read-only saymo dry-run command and LaunchReadinessReport reuse
  - phase: 47-source-type-pause-presets
    provides: Source-aware F5 prepared and response-cache metadata fields
provides:
  - RED contracts for dry-run --prepare-source source-only creation
  - RED contracts for caller-aware launch-readiness mode and rerun commands
  - RED contracts for prepared-audio, response-cache, and cloned-voice metadata visibility
  - RED contracts for targeted repair guidance without default --force
affects: [49-02, dry-run, call-ready, launch-readiness, launch-cache, launch-sources]

tech-stack:
  added: []
  patterns:
    - "RED-only pytest contracts exercise future mode/rerun_command parameters without production changes."
    - "Provider/audio/call-control tails are monkeypatched inert when tests target source-only behavior."
    - "Private source, response, secret, and voice-reference text remains excluded from serialized diagnostics."

key-files:
  created:
    - .planning/phases/49-source-prepared-audio-cache-and-voice-readiness/49-01-SUMMARY.md
  modified:
    - tests/test_dry_run_cli.py
    - tests/analysis/test_launch_readiness.py
    - tests/analysis/test_cache_advice.py
    - tests/analysis/test_response_cache.py

key-decisions:
  - "Kept Wave 1 strictly RED and test-only; production code remains untouched for Plan 49-02."
  - "Used dry-run mode and rerun_command test contracts as the small caller context expected by the GREEN plan."
  - "Kept response-cache --force only as non-default guidance by asserting it is absent from recommended action text."

patterns-established:
  - "Dry-run source creation is represented as prepare=True plus mode=\"dry-run\", not as a broad repair command."
  - "Prepared and response-cache diagnostics assert source_type, purpose, preset ids, and sanitized counts/examples."
  - "Cloned-voice readiness checks assert selector/manifest metadata only and avoid trainer/checkpoint/dataset mutation language."

requirements-completed: [SRC-01, SRC-02, SRC-03, CACHE-01, CACHE-02, VOICE-01]

duration: 6min
completed: 2026-07-10
---

# Phase 49 Plan 01: Source, Prepared Audio, Cache, And Voice Readiness RED Summary

**Dry-run source, prepared-audio, response-cache, and cloned-voice readiness behavior is now locked as failing RED pytest contracts for the GREEN implementation.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-10T12:55:20Z
- **Completed:** 2026-07-10T13:01:10Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added CLI RED tests for `saymo dry-run --prepare-source`, `mode="dry-run"` collector calls, standalone `--prepare` rejection, and dry-run static safety guards.
- Added launch-readiness RED tests for source note create/no-overwrite behavior, dry-run rerun/action routing, prepared-audio metadata, and cloned-voice read-only guidance.
- Added response-cache RED tests for profile-targeted non-force repair guidance and source-aware coverage metadata without raw response text.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add RED dry-run source flag and safety CLI contracts** - `954442a` (test)
2. **Task 2: Add RED readiness metadata and targeted repair contracts** - `b6b7bf6` (test)

## Files Created/Modified

- `tests/test_dry_run_cli.py` - Adds dry-run `--prepare-source`, mode, standalone `--prepare` rejection, rerun, and static non-mutation contracts.
- `tests/analysis/test_launch_readiness.py` - Adds dry-run source create/no-overwrite, rerun routing, prepared metadata, and cloned-voice read-only contracts.
- `tests/analysis/test_cache_advice.py` - Adds no-default-force response-cache repair guidance regression.
- `tests/analysis/test_response_cache.py` - Adds dry-run response-cache coverage metadata contract with private response text exclusion.

## Decisions Made

- Followed the plan exactly as a RED-only wave and did not edit production code.
- Used temporary vaults/caches and monkeypatches only; no TTS synthesis, playback, recording, cache deletion, retraining, downloads, or protected `.saymo` asset mutation.

## Verification

- `uv run pytest tests/test_dry_run_cli.py -q` -> RED: `3 failed, 6 passed`; failures are missing `mode="dry-run"` and `--prepare-source`.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py -q` -> RED: `5 failed, 41 passed`; failures are missing `mode` and `rerun_command` parameters.
- `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py -q` -> RED: `8 failed, 47 passed`.
- `uv run pytest tests/test_call_ready_cli.py::test_call_ready_prints_top_level_result tests/test_call_ready_cli.py::test_call_ready_json_is_sanitized -q` -> `2 passed`.

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None.

## Issues Encountered

None. The failing pytest output is the expected RED state for missing Phase 49 production behavior.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 49-02 can implement the missing `--prepare-source`, launch-readiness `mode`, source-specific action/rerun routing, prepared metadata fields, and cache/voice `rerun_command` parameters against these RED contracts.

---
*Phase: 49-source-prepared-audio-cache-and-voice-readiness*
*Completed: 2026-07-10*

## Self-Check: PASSED

- Found `.planning/phases/49-source-prepared-audio-cache-and-voice-readiness/49-01-SUMMARY.md`.
- Found `tests/test_dry_run_cli.py`.
- Found `tests/analysis/test_launch_readiness.py`.
- Found `tests/analysis/test_cache_advice.py`.
- Found `tests/analysis/test_response_cache.py`.
- Found commit `954442a`.
- Found commit `b6b7bf6`.
