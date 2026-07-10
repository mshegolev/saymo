---
phase: 50-provider-audio-and-call-control-health
plan: "02"
subsystem: dry-run
tags: [pytest, dry-run, provider-readiness, audio-routing, launchagent, call-control]

requires:
  - phase: 50-provider-audio-and-call-control-health
    provides: RED contracts from Plan 50-01 for provider/audio dry-run context and call-control safety
  - phase: 49-source-prepared-audio-cache-and-voice-readiness
    provides: Dry-run mode and caller-aware launch-readiness rerun routing
  - phase: 37-provider-and-audio-remediation
    provides: Provider tab, audio route, capability, and permission readiness collectors
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: Read-only LaunchAgent, daemon heartbeat, and hotkey status classification
provides:
  - Dry-run-aware provider/audio readiness reruns and action wording
  - Provider/audio collector signatures with optional `rerun_command` and `mode`
  - Launch-readiness dry-run context wiring into provider/audio checks
  - Verified call-control status/action clarity without new lifecycle or probe calls
affects: [dry-run, call-ready, launch-readiness, provider-audio, launch-agent, call-control]

tech-stack:
  added: []
  patterns:
    - "Provider/audio readiness collectors accept optional caller context while preserving call-ready defaults."
    - "Launch readiness computes the dry-run rerun once and forwards it only to collectors that support the new context."
    - "Call-control readiness remains status-only; install/start/restart/probe commands stay as operator text."

key-files:
  created:
    - .planning/phases/50-provider-audio-and-call-control-health/50-02-SUMMARY.md
  modified:
    - saymo/analysis/provider_audio_readiness.py
    - saymo/analysis/launch_readiness.py

key-decisions:
  - "Kept provider/audio dry-run support as optional `rerun_command` and `mode` parameters instead of adding a separate diagnostics subsystem."
  - "Preserved call-ready monkeypatch compatibility by sending new provider/audio kwargs only when dry-run context is supported."
  - "Left `saymo/analysis/launch_agent.py` unchanged because Task 2 RED contracts already passed with existing classification/action wording."

patterns-established:
  - "Dry-run provider/audio blockers rerun through `saymo dry-run -p <profile> --provider <provider>`."
  - "Call-ready provider/audio defaults still rerun through `saymo call-ready -p <profile> --provider <provider>`."
  - "Provider/audio action text names manual commands such as `saymo test-devices` and never promises automatic repair."

requirements-completed: [ENV-01, ENV-02, ENV-03]

duration: 5min
completed: 2026-07-10
---

# Phase 50 Plan 02: Provider, Audio, And Call-Control Health Summary

**Dry-run provider/audio readiness now uses dry-run reruns and safe operator actions, while call-control health remains read-only with verified install/start/restart/status/probe guidance.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-10T14:00:33Z
- **Completed:** 2026-07-10T14:05:14Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added optional `rerun_command` and `mode` parameters to provider/audio readiness collectors.
- Routed `collect_launch_readiness(..., mode="dry-run")` provider/audio checks to `saymo dry-run -p <profile> --provider <provider>`.
- Updated provider, permission, and provider-capability action text so dry-run mode references dry-run reruns instead of call-ready.
- Preserved old call-ready defaults and existing monkeypatched tests that expose the pre-Phase-50 provider/audio signature.
- Verified call-control action clarity and safety without editing `launch_agent.py` because existing behavior already satisfied the RED contracts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement provider/audio dry-run rerun and action routing** - `ea4bd8a` (feat)
2. **Task 2: Tighten call-control action clarity and safety if RED tests require it** - `6c681f4` (chore, no code changes required)

## Files Created/Modified

- `saymo/analysis/provider_audio_readiness.py` - Adds dry-run caller context to provider/audio collectors and dry-run-specific rerun/action wording.
- `saymo/analysis/launch_readiness.py` - Threads dry-run provider/audio context from launch readiness and preserves legacy collector compatibility.
- `.planning/phases/50-provider-audio-and-call-control-health/50-02-SUMMARY.md` - Documents execution results.

## Decisions Made

- Used optional collector parameters rather than a new dry-run provider/audio result model.
- Kept call-ready behavior backward compatible by not passing new kwargs for call-ready mode.
- Added a small signature guard in launch readiness so old no-op provider/audio monkeypatches still work during dry-run tests.
- Did not edit `saymo/analysis/launch_agent.py`; Task 2 verification already passed the action wording and read-only safety contracts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Preserved legacy provider/audio monkeypatch compatibility**
- **Found during:** Task 1 (Implement provider/audio dry-run rerun and action routing)
- **Issue:** Existing dry-run tests use inert provider/audio monkeypatches with the old no-kwargs signature; blindly forwarding dry-run kwargs would break unrelated compatibility tests.
- **Fix:** Added `_accepts_provider_audio_context()` in launch readiness so dry-run context is forwarded to the real collector and newer fakes, while old no-op fakes remain supported.
- **Files modified:** `saymo/analysis/launch_readiness.py`
- **Verification:** Task 1 focused tests passed, then full Phase 50 and full-suite verification passed.
- **Committed in:** `ea4bd8a`

---

**Total deviations:** 1 auto-fixed (1 bug/compatibility issue)
**Impact on plan:** The adjustment preserved backward compatibility without expanding behavior or weakening dry-run safety.

## Authentication Gates

None.

## Issues Encountered

None. Task 2 required no production edit because the existing call-control status/action mapping already passed the RED contracts.

## Verification

- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/analysis/test_launch_agent.py tests/test_dry_run_cli.py tests/test_call_control_cli.py -q` -> RED baseline before implementation: `2 failed, 52 passed`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py::test_collect_launch_readiness_passes_dry_run_context_to_provider_audio tests/test_dry_run_cli.py -q` -> `17 passed`.
- `uv run pytest tests/analysis/test_launch_agent.py tests/analysis/test_launch_readiness.py tests/test_call_control_cli.py tests/test_dry_run_cli.py -q` -> `47 passed`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/analysis/test_launch_agent.py tests/test_dry_run_cli.py tests/test_call_control_cli.py -q` -> `54 passed`.
- `uv run pytest tests/test_call_ready_cli.py tests/test_dry_run_cli.py tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py -q` -> `63 passed`.
- Static safety grep for provider mutators, playback/recording, config/audio-volume writers, probe execution, and LaunchAgent lifecycle helpers in dry-run/readiness files -> no matches.
- `uv run pytest -q` -> `635 passed`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 50 is complete. Phase 51 can build on the provider/audio/control dry-run checks to save and reuse sanitized dry-run evidence in rehearsal, scorecards, safety-soak, and latest-vs-previous comparisons.

---
*Phase: 50-provider-audio-and-call-control-health*
*Completed: 2026-07-10*

## Self-Check: PASSED

- Found `.planning/phases/50-provider-audio-and-call-control-health/50-02-SUMMARY.md`.
- Found `saymo/analysis/provider_audio_readiness.py`.
- Found `saymo/analysis/launch_readiness.py`.
- Found commit `ea4bd8a`.
- Found commit `6c681f4`.
