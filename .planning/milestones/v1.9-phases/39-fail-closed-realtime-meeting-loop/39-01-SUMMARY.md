---
phase: 39-fail-closed-realtime-meeting-loop
plan: "01"
subsystem: realtime-startup-gate
tags: [saymo, realtime, call-ready, launch-readiness, fail-closed, pytest]

requires:
  - phase: 36-call-ready-preflight-and-cache-gate
    provides: shared LaunchReadinessReport, collect_launch_readiness, and grouped remediation rendering
  - phase: 37-provider-and-audio-remediation
    provides: non-destructive provider/audio launch-readiness rows
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: call-control daemon readiness rows consumed by call-ready
provides:
  - RealtimeLaunchGate helper over the shared call-ready launch report
  - fail-closed saymo auto startup gate before realtime setup begins
  - thin saymo realtime alias that delegates to the same auto path
  - RED/GREEN tests for blocked startup, remediation reuse, aliasing, and no unsafe gate options
affects: [phase-39, phase-40, realtime-loop, call-ready, live-control]

tech-stack:
  added: []
  patterns:
    - TDD RED/GREEN commit split for realtime startup gating
    - Reuse collect_launch_readiness and render_launch_readiness instead of duplicating launch checks
    - Click command alias shares one startup helper with the primary auto command

key-files:
  created:
    - saymo/analysis/realtime_gate.py
    - tests/analysis/test_realtime_gate.py
    - .planning/phases/39-fail-closed-realtime-meeting-loop/39-01-SUMMARY.md
  modified:
    - saymo/commands/core.py
    - tests/test_auto_qa_flow.py

key-decisions:
  - "Realtime startup gates through collect_launch_readiness(..., prepare=False) and uses launch-readiness-ready / launch-readiness-blocked as stable reasons."
  - "saymo realtime is a thin alias over the same _auto startup path as saymo auto, with no unsafe readiness bypass option."
  - "Blocked startup prints render_launch_readiness output before returning, so call-ready remediation remains the single operator-facing fix path."

patterns-established:
  - "evaluate_realtime_launch_gate resolves provider from the meeting profile when no override is supplied."
  - "render_realtime_launch_block appends the stable realtime blocked line after grouped call-ready remediation."
  - "_auto evaluates the launch gate before cached-audio stat, device lookup, provider construction, AudioCapture, LocalWhisper, response-cache setup, TTS warmup, hotkeys, or loops."

requirements-completed: [REAL-01, REAL-02]

duration: 18min
completed: 2026-07-08T17:20:19Z
---

# Phase 39 Plan 01: Realtime Startup Gate Summary

**Shared call-ready launch gate for `saymo auto` and the `saymo realtime` alias, blocking before realtime capture, STT, provider, hotkey, cache, or TTS setup.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-07-08T17:02:00Z
- **Completed:** 2026-07-08T17:20:19Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `saymo.analysis.realtime_gate` with `RealtimeLaunchGate`, `evaluate_realtime_launch_gate()`, and `render_realtime_launch_block()`.
- Wired `_auto()` to evaluate the shared launch-readiness report before any realtime setup, returning fail-closed with `launch-readiness-blocked`.
- Added `saymo realtime` as a thin Click alias over the same `_auto()` path used by `saymo auto`.
- Added tests proving provider resolution, shared readiness invocation, blocked remediation rendering, blocked-before-setup behavior, alias delegation, and absence of unsafe help options.

## Task Commits

1. **Task 1 RED: Launch-gate startup tests** - `170a8f0` (`test`)
2. **Task 2 GREEN: Shared realtime launch gate** - `2403158` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/realtime_gate.py` - Realtime startup gate dataclass, evaluator, and blocked renderer over launch readiness.
- `saymo/commands/core.py` - Shared auto/realtime startup helper and early `_auto()` launch gate.
- `tests/analysis/test_realtime_gate.py` - Unit coverage for helper provider resolution, ready/blocked reasons, and remediation reuse.
- `tests/test_auto_qa_flow.py` - Startup gate, realtime alias, and no unsafe gate option regressions.
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-01-SUMMARY.md` - Execution evidence and scope handoff.

## Decisions Made

- `prepare=False` is hard-coded for realtime startup gate evaluation so `saymo auto` and `saymo realtime` stay non-mutating.
- The gate reason labels are intentionally stable: `launch-readiness-ready` and `launch-readiness-blocked`.
- The realtime alias was added now because the plan requested alias regression coverage; it delegates to `_run_auto_start()` and does not introduce separate readiness logic.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RED verification failed as expected with `ModuleNotFoundError: No module named 'saymo.analysis.realtime_gate'`; the wrapper command exited 0 because the tests failed before implementation.
- No auth gates, architecture changes, or out-of-scope fixes occurred.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_realtime_gate.py tests/test_auto_qa_flow.py -q; test $? -ne 0'`
  - RED result: expected collection failure for missing `saymo.analysis.realtime_gate`; wrapper exited 0.
- `uv run pytest tests/analysis/test_realtime_gate.py tests/test_auto_qa_flow.py -q`
  - Result: `47 passed in 0.21s`.
- `uv run pytest tests/test_call_ready_cli.py tests/analysis/test_launch_readiness.py -q`
  - Result: `19 passed in 1.92s`.
- `bash -lc '! rg "bypass|ignore_readiness|ignore-readiness|unsafe.*gate|no-gate" saymo/commands/core.py'`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/realtime_gate.py'`
  - Result: passed.
- `git diff --check`
  - Result: passed.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 39 can now move to response-cache and cloned-voice fail-closed policy. This plan intentionally did not change automatic cache-miss behavior, provider pre-play drift checks, manual standup policy, realtime event files, Phase 40 reporting, or safety-soak.

## Self-Check: PASSED

- Created/modified files found: `saymo/analysis/realtime_gate.py`, `saymo/commands/core.py`, `tests/analysis/test_realtime_gate.py`, `tests/test_auto_qa_flow.py`, and this summary.
- Task commits found: `170a8f0` and `2403158`.
- Required RED, focused GREEN, launch-readiness regression, static gate, non-destructive, and diff-check validation results are recorded above.

---
*Phase: 39-fail-closed-realtime-meeting-loop*
*Completed: 2026-07-08*
