---
phase: 49-source-prepared-audio-cache-and-voice-readiness
plan: "02"
subsystem: dry-run
tags: [pytest, dry-run, launch-readiness, source-audio, response-cache, voice-metadata]

requires:
  - phase: 48-dry-run-orchestrator-and-result-contract
    provides: Read-only saymo dry-run command and LaunchReadinessReport reuse
  - phase: 47-source-type-pause-presets
    provides: Source-aware F5 prepared and response-cache metadata fields
  - phase: 49-source-prepared-audio-cache-and-voice-readiness
    provides: RED contracts from Plan 49-01
provides:
  - Dry-run source-only daily-note preparation with `--prepare-source`
  - Caller-aware source, prepared-audio, response-cache, and cloned-voice rerun guidance
  - Prepared-audio and response-cache launch metadata with source-type F5 preset fields
  - Targeted cache and voice repair commands without default force rebuilds or mutation paths
affects: [dry-run, call-ready, launch-readiness, launch-sources, launch-cache, cache-advice]

tech-stack:
  added: []
  patterns:
    - "Launch readiness uses mode=\"dry-run\" as caller context while preserving call-ready defaults."
    - "Readiness collectors accept optional rerun/action strings instead of branching into separate dry-run implementations."
    - "Prepared/cache diagnostics surface hashes, counts, profile state, and preset ids without raw source or response text."

key-files:
  created:
    - .planning/phases/49-source-prepared-audio-cache-and-voice-readiness/49-02-SUMMARY.md
  modified:
    - saymo/commands/dry_run.py
    - saymo/analysis/launch_readiness.py
    - saymo/analysis/launch_sources.py
    - saymo/analysis/launch_cache.py

key-decisions:
  - "Added only `--prepare-source` to dry-run; standalone `--prepare` remains invalid for dry-run."
  - "Kept `prepare=True` scoped to selected daily-note creation through existing Obsidian helpers."
  - "Kept response-cache force rebuild as warning-only guidance, never the default repair command."
  - "Used selector/manifest metadata for cloned-voice readiness and avoided training, dataset, checkpoint, model, provider, and audio mutation paths."

patterns-established:
  - "Dry-run readiness reruns use `saymo dry-run -p <profile> --provider <provider>` for source, prepared, cache, and voice blockers."
  - "Missing source action uses `saymo dry-run -p <profile> --provider <provider> --prepare-source`."
  - "Blocked cloned voice readiness points to `saymo voice-profile check --profile <voice_profile>` and `saymo prepare -p <profile>`."

requirements-completed: [SRC-01, SRC-02, SRC-03, CACHE-01, CACHE-02, VOICE-01]

duration: 9min
completed: 2026-07-10
---

# Phase 49 Plan 02: Source, Prepared Audio, Cache, And Voice Readiness Summary

**Dry-run now verifies and optionally creates only the selected source note, while surfacing prepared-audio, response-cache, and cloned-voice readiness metadata with targeted non-mutating repair commands.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-07-10T13:05:24Z
- **Completed:** 2026-07-10T13:14:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `saymo dry-run --prepare-source` and threaded `mode="dry-run"` through launch readiness.
- Routed dry-run source, prepared-audio, response-cache, and cloned-voice rerun commands back to `saymo dry-run`.
- Exposed prepared-audio metadata for source SHA, selected engine, voice profile approval, and F5 `prepared` preset ids.
- Preserved response-cache guidance as `saymo prepare-responses -p <profile>` without default `--force`.
- Added cloned-voice guidance that names explicit operator commands without touching voice assets.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement dry-run source flag and source/prepared caller context** - `f8414ed` (feat)
2. **Task 2: Implement cache and voice dry-run guidance without mutation paths** - `97c89d2` (feat)

## Files Created/Modified

- `saymo/commands/dry_run.py` - Adds `--prepare-source` and calls launch readiness with `prepare=prepare_source, mode="dry-run"`.
- `saymo/analysis/launch_readiness.py` - Adds caller-mode routing helpers and dry-run rerun/action wiring.
- `saymo/analysis/launch_sources.py` - Adds source/prepared optional rerun/action parameters and F5 preset metadata fields.
- `saymo/analysis/launch_cache.py` - Adds optional cache/voice rerun commands and explicit cloned-voice remediation text.
- `.planning/phases/49-source-prepared-audio-cache-and-voice-readiness/49-02-SUMMARY.md` - Documents execution results.

## Decisions Made

- Used a small `mode` parameter and optional rerun/action strings instead of a separate dry-run result model.
- Kept call-ready defaults backward compatible by making downstream caller context optional.
- Left `cache_advice.py` unchanged because its action already used the non-force rebuild command required by Plan 49-01.

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None.

## Issues Encountered

- Task 1 verification file also covered the Task 2 voice rerun contract. The Task 2 implementation was applied before the first verification run, while commits still remained split by production file ownership.

## Verification

- `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py -q` -> RED before implementation: `8 failed, 47 passed`.
- `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py -q` -> `29 passed`.
- `uv run pytest tests/test_dry_run_cli.py tests/test_call_ready_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py tests/analysis/test_cache_metadata.py tests/tts/test_selector.py -q` -> `80 passed`.
- Static safety check for mutation-path references -> no matches.
- `uv run pytest -q` -> `631 passed`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 49 is complete. Phase 50 can build on dry-run source/cache/voice readiness to cover provider tab state, BlackHole routing, audio devices, and call-control health.

---
*Phase: 49-source-prepared-audio-cache-and-voice-readiness*
*Completed: 2026-07-10*

## Self-Check: PASSED

- Found `.planning/phases/49-source-prepared-audio-cache-and-voice-readiness/49-02-SUMMARY.md`.
- Found `saymo/commands/dry_run.py`.
- Found `saymo/analysis/launch_readiness.py`.
- Found `saymo/analysis/launch_sources.py`.
- Found `saymo/analysis/launch_cache.py`.
- Found commit `f8414ed`.
- Found commit `97c89d2`.
