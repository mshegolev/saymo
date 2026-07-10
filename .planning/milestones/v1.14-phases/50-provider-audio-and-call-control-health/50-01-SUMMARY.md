---
phase: 50-provider-audio-and-call-control-health
plan: "01"
subsystem: testing
tags: [pytest, dry-run, provider-readiness, audio-routing, launchagent, call-control]

requires:
  - phase: 49-source-prepared-audio-cache-and-voice-readiness
    provides: Dry-run mode, shared LaunchReadinessReport, and caller-aware source/cache/voice rerun routing
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: LaunchAgent status classifier, daemon heartbeat status, and call-control CLI boundaries
  - phase: 37-provider-and-audio-remediation
    provides: Provider tab, Chrome permission, BlackHole, audio-device, and macOS permission collectors
provides:
  - RED contracts for dry-run provider/audio rerun context and safe metadata
  - RED contract for launch readiness passing dry-run context into provider/audio checks
  - Regression guards for exact LaunchAgent action/rerun commands
  - Regression guards preventing dry-run call-control probe/lifecycle mutations and command/audit writes
affects: [50-02, dry-run, call-ready, launch-readiness, provider-audio, launch-agent, call-control]

tech-stack:
  added: []
  patterns:
    - "RED-only pytest contracts use optional rerun_command and mode parameters without production changes."
    - "Provider/audio and call-control health checks are monkeypatched at OS/provider/audio boundaries."
    - "Dry-run safety is guarded by both runtime monkeypatch failures and static forbidden-reference checks."

key-files:
  created:
    - .planning/phases/50-provider-audio-and-call-control-health/50-01-SUMMARY.md
  modified:
    - tests/analysis/test_provider_audio_readiness.py
    - tests/analysis/test_launch_readiness.py
    - tests/analysis/test_launch_agent.py
    - tests/test_dry_run_cli.py
    - tests/test_call_control_cli.py

key-decisions:
  - "Kept Plan 50-01 strictly RED/test-only; production code remains untouched for Plan 50-02."
  - "Used optional `rerun_command` and `mode` as the dry-run provider/audio caller context expected by the GREEN plan."
  - "Kept call-control probe, LaunchAgent lifecycle, and command/audit writes out of dry-run diagnostics."

patterns-established:
  - "Dry-run provider/audio blockers rerun through `saymo dry-run -p <profile> --provider <provider>` while call-ready defaults stay backward compatible."
  - "LaunchAgent status tests pin operator commands for install, start, restart, status, and probe guidance."
  - "Call-control dry-run tests must monkeypatch probe and launchd lifecycle helpers as forbidden."

requirements-completed: [ENV-01, ENV-02, ENV-03]

duration: 7min
completed: 2026-07-10
---

# Phase 50 Plan 01: Provider, Audio, And Call-Control Health RED Summary

**Dry-run provider/audio readiness and call-control health are now locked as failing RED pytest contracts plus read-only regression guards for the GREEN implementation.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-10T13:49:48Z
- **Completed:** 2026-07-10T13:56:09Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added provider/audio RED coverage for dry-run rerun routing, safe provider/audio metadata, sanitized provider errors, permission blocker guidance, and call-ready compatibility.
- Added launch-readiness RED coverage requiring `collect_launch_readiness(..., mode="dry-run")` to pass `rerun_command` and `mode` into provider/audio checks.
- Added LaunchAgent command wording guards for install/start/restart/status and crash/hotkey permission classifications.
- Added dry-run call-control guards proving status collection stays read-only and only recommends explicit status/probe/lifecycle commands.
- Extended static dry-run safety checks to forbid provider/audio/control repair APIs, launchd lifecycle helpers, probe execution, and command/audit log writes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add RED provider/audio dry-run routing contracts** - `dd2551c` (test)
2. **Task 2: Add RED call-control action clarity and no-auto-repair guards** - `745d056` (test)

## Files Created/Modified

- `tests/analysis/test_provider_audio_readiness.py` - Adds dry-run provider/audio caller context, metadata, sanitization, permission, and call-ready compatibility contracts.
- `tests/analysis/test_launch_readiness.py` - Adds provider/audio dry-run wiring contract and read-only call-control dry-run action/rerun regression.
- `tests/analysis/test_launch_agent.py` - Pins exact LaunchAgent classification action/rerun command strings.
- `tests/test_dry_run_cli.py` - Extends static no-auto-repair guard for call-control, launchd, command, and audit paths.
- `tests/test_call_control_cli.py` - Confirms status JSON does not create command or audit logs.
- `.planning/phases/50-provider-audio-and-call-control-health/50-01-SUMMARY.md` - Documents execution results.

## Decisions Made

- Followed the plan exactly as a RED-only wave and did not edit production code.
- Kept all provider, audio, launchd, heartbeat, and hotkey evidence monkeypatched or in `tmp_path`.
- Treated call-control status/probe/lifecycle separation as regression coverage that already mostly passes before Plan 50-02.

## Verification

- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py::test_collect_launch_readiness_passes_dry_run_context_to_provider_audio -q` -> RED: `2 failed, 6 passed`; failures are missing provider/audio `rerun_command` parameter and missing dry-run context wiring.
- `uv run pytest tests/analysis/test_launch_agent.py tests/analysis/test_launch_readiness.py tests/test_dry_run_cli.py tests/test_call_control_cli.py -q` -> RED: `1 failed, 46 passed`; the only failure is the already-expected provider/audio dry-run context wiring contract.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/analysis/test_launch_agent.py tests/test_dry_run_cli.py tests/test_call_control_cli.py -q` -> RED: `2 failed, 52 passed`; both failures are intended missing Phase 50-02 production behavior.

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None.

## Issues Encountered

None. The failing pytest output is the expected RED state for missing Phase 50 provider/audio dry-run caller context.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 50-02 can implement optional provider/audio `rerun_command` and `mode` parameters, thread dry-run context from launch readiness, and refine call-control action clarity against these RED contracts.

---
*Phase: 50-provider-audio-and-call-control-health*
*Completed: 2026-07-10*

## Self-Check: PASSED

- Found `.planning/phases/50-provider-audio-and-call-control-health/50-01-SUMMARY.md`.
- Found `tests/analysis/test_provider_audio_readiness.py`.
- Found `tests/analysis/test_launch_readiness.py`.
- Found `tests/analysis/test_launch_agent.py`.
- Found `tests/test_dry_run_cli.py`.
- Found `tests/test_call_control_cli.py`.
- Found commit `dd2551c`.
- Found commit `745d056`.
