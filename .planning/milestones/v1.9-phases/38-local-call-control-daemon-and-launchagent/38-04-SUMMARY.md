---
phase: 38-local-call-control-daemon-and-launchagent
plan: "04"
subsystem: live-control-audit-routing
tags: [live-control, call-control, audit, daemon-hotkeys, click, pytest]

requires:
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: foreground daemon heartbeat and daemon hotkey queueing from 38-01
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: LaunchAgent lifecycle and status surface from 38-02/38-03
provides:
  - call-control action CLI that queues normalized existing live-control commands
  - backward-compatible audit correlation fields for command_id, probe_id, and sanitized payload
  - daemon hotkey payload sanitization helper
  - trusted-daemon seam for skipping duplicate auto hotkey listeners
affects: [phase-38, live-control, call-control-daemon, realtime-gating, reachability-probe]

tech-stack:
  added: []
  patterns:
    - bounded live-control metadata sanitizer for command/audit payloads
    - existing commands.jsonl remains the only action queue protocol
    - auto-mode can opt out of local hotkeys when daemon hotkeys are trusted

key-files:
  created:
    - .planning/phases/38-local-call-control-daemon-and-launchagent/38-04-SUMMARY.md
  modified:
    - saymo/analysis/live_control.py
    - saymo/analysis/control_daemon.py
    - saymo/commands/call_control.py
    - saymo/commands/core.py
    - tests/analysis/test_live_control.py
    - tests/analysis/test_control_daemon.py
    - tests/test_live_control_cli.py
    - tests/test_call_control_cli.py
    - tests/test_auto_qa_flow.py

key-decisions:
  - "call-control action uses the existing live-control queue with source=daemon_cli; no new protocol or action names were introduced."
  - "Audit command correlation is optional and bounded so existing audit readers continue to work without new required fields."
  - "The trusted daemon path is an internal opt-in seam; default saymo auto behavior still registers local hotkeys."

patterns-established:
  - "sanitized_control_payload() allows probe_id metadata and drops raw meeting/private payload fields."
  - "_append_control_action_audit() is the reusable auto audit path for queued commands with command_id/probe_id preservation."

requirements-completed: [CTRL-04]

duration: 4min
completed: 2026-07-08T16:20:32Z
---

# Phase 38 Plan 04: Action Routing and Audit Semantics Summary

**Call-control actions now reuse commands.jsonl with sanitized audit correlation for daemon, CLI, and future reachability probes**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-08T16:16:21Z
- **Completed:** 2026-07-08T16:20:32Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added RED tests proving `saymo call-control action`, existing `live-control-action`, daemon hotkey source/payload conventions, audit correlation, and duplicate-hotkey prevention contracts.
- Added `saymo call-control action --profile/-p --action --base-dir --probe-id` to queue normalized existing actions with source `daemon_cli`.
- Extended `append_control_audit()` with optional `command_id`, `probe_id`, and sanitized payload fields while preserving old audit fields.
- Routed auto command-loop audits through a reusable helper that preserves command id and probe id from consumed commands.
- Added an internal `disable_local_hotkeys` seam so a trusted daemon can own hotkeys later without changing default auto behavior.

## Task Commits

1. **Task 1: Write RED action routing, audit correlation, and duplicate-hotkey tests** - `a2c6e3e` (test)
2. **Task 2: Implement existing-action routing and audit preservation** - `27d3f4b` (feat)

## Files Created/Modified

- `saymo/analysis/live_control.py` - Adds bounded payload sanitization and optional audit correlation fields.
- `saymo/analysis/control_daemon.py` - Adds `queue_daemon_hotkey_command()` and routes daemon hotkeys through sanitized source/payload conventions.
- `saymo/commands/call_control.py` - Adds `call-control action` CLI using existing action normalization and command queueing.
- `saymo/commands/core.py` - Adds auto audit helper, command correlation extraction, and trusted-daemon local-hotkey disable seam.
- `tests/analysis/test_live_control.py` - Adds audit correlation and sanitized payload coverage.
- `tests/analysis/test_control_daemon.py` - Adds daemon hotkey source and payload sanitization coverage.
- `tests/test_live_control_cli.py` - Confirms existing `live-control-action` source/output behavior remains unchanged.
- `tests/test_call_control_cli.py` - Adds `call-control action` queueing coverage.
- `tests/test_auto_qa_flow.py` - Adds auto audit preservation and duplicate-hotkey seam coverage.

## Decisions Made

- Use only existing normalized live-control action names; `hard-disable` still queues as `hard_disable`.
- Allow `probe_id` metadata now, but leave actual reachability probe waiting/reporting to Plan 38-05.
- Keep `saymo auto` default behavior unchanged; duplicate-hotkey prevention is only active when an internal caller opts into `disable_local_hotkeys=True`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RED verification failed as expected before implementation with missing `queue_daemon_hotkey_command` and `_append_control_action_audit` imports.
- A non-required `python -m compileall` check hit the local pyenv shim; rerunning with `uv run python -m compileall -q ...` passed.

## Validation Output

- `bash -lc 'uv run pytest tests/analysis/test_live_control.py tests/analysis/test_control_daemon.py tests/test_live_control_cli.py tests/test_call_control_cli.py tests/test_auto_qa_flow.py -q; test $? -ne 0'` - exited 0 with expected RED import errors.
- `uv run python -m compileall -q saymo/analysis/live_control.py saymo/analysis/control_daemon.py saymo/commands/call_control.py saymo/commands/core.py` - passed.
- `uv run pytest tests/analysis/test_live_control.py tests/analysis/test_control_daemon.py tests/test_live_control_cli.py tests/test_call_control_cli.py tests/test_auto_qa_flow.py -q` - `59 passed in 0.27s`.
- `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py -q` - `52 passed in 1.32s`.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/control_daemon.py saymo/analysis/launch_agent.py saymo/commands/call_control.py'` - passed with no matches.
- `git diff --check` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 38-05 can add an explicit reachability probe using the queued command id and sanitized `probe_id` now preserved in auto audit events. Manual macOS GUI-session verification of LaunchAgent hotkey permissions remains a Phase 38 residual risk, as already tracked.

## Self-Check: PASSED

- Created/modified files exist: `saymo/analysis/live_control.py`, `saymo/analysis/control_daemon.py`, `saymo/commands/call_control.py`, `saymo/commands/core.py`, test files, and this summary.
- Task commits exist: `a2c6e3e` and `27d3f4b`.

---
*Phase: 38-local-call-control-daemon-and-launchagent*
*Completed: 2026-07-08T16:20:32Z*
