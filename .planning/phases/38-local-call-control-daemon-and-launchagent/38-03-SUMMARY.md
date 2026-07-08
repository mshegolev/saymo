---
phase: 38-local-call-control-daemon-and-launchagent
plan: "03"
subsystem: launchagent-diagnostics
tags: [live-control, launchagent, heartbeat, diagnostics, json, pytest]

requires:
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: foreground daemon heartbeat model from 38-01
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: LaunchAgent lifecycle, plist hashing, and launchctl command boundary from 38-02
provides:
  - read-only call-control agent health classifications
  - heartbeat-fresh running truth for LaunchAgent status
  - human and JSON call-control-agent status output
affects: [phase-38, call-control-agent, call-ready, realtime-gating]

tech-stack:
  added: []
  patterns:
    - heartbeat freshness is the running truth for call-control daemon status
    - launchctl print output is bounded best-effort diagnostic metadata only
    - status JSON uses the CallControlAgentStatus dataclass serialization

key-files:
  created:
    - .planning/phases/38-local-call-control-daemon-and-launchagent/38-03-SUMMARY.md
  modified:
    - saymo/analysis/launch_agent.py
    - saymo/commands/call_control.py
    - tests/analysis/test_launch_agent.py
    - tests/test_call_control_cli.py

key-decisions:
  - "Call-control agent running state is defined as loaded plus fresh daemon heartbeat; launchctl print PID text is no longer trusted as running truth."
  - "Daemon-side hotkey registration status from heartbeat is the permission signal for agent status."
  - "Status output is read-only and exposes action/rerun guidance without starting, stopping, bootstrapping, or queueing commands."

patterns-established:
  - "CallControlAgentStatus carries profile, label, plist/log paths, booleans, classification, detail, action, rerun, and sanitized metadata."
  - "collect_call_control_agent_status() combines plist hash, optional plutil lint, launchctl print return code/excerpts, heartbeat freshness, and hotkey status through an injectable runner."

requirements-completed: [CTRL-03]

duration: 5min
completed: 2026-07-08T16:10:17Z
---

# Phase 38 Plan 03: Daemon Health Diagnostics Summary

**Read-only call-control agent diagnostics with heartbeat-based running truth and JSON status output**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-08T16:05:21Z
- **Completed:** 2026-07-08T16:10:17Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `CallControlAgentStatus` and `collect_call_control_agent_status()` for `not_installed`, `installed_not_loaded`, `running`, `stale_heartbeat`, `plist_drift`, `crash_loop`, `hotkey_permission_blocked`, and `status_unavailable`.
- Updated `saymo call-control-agent status` to render classification, heartbeat freshness, hotkey status, detail, action, rerun, plist path, and log paths.
- Added `--json` status output with sanitized dataclass fields and metadata for later launch-readiness artifacts.
- Proved status stays read-only through tests and static grep: no lifecycle mutators, command queue writes, provider mutations, audio mutations, config writes, or kill commands.

## Task Commits

1. **Task 1: Write RED daemon status classification tests** - `879ac91` (test)
2. **Task 2: Implement read-only status diagnostics** - `305fceb` (feat)

## Files Created/Modified

- `saymo/analysis/launch_agent.py` - Adds `CallControlAgentStatus`, status aggregation, classification, bounded launchctl metadata, heartbeat loading, and action/rerun guidance.
- `saymo/commands/call_control.py` - Switches status to the new collector and adds human plus `--json` output.
- `tests/analysis/test_launch_agent.py` - Adds RED/GREEN coverage for all required status classifications.
- `tests/test_call_control_cli.py` - Adds read-only JSON status coverage and updates human status expectations to heartbeat running truth.
- `.planning/phases/38-local-call-control-daemon-and-launchagent/38-03-SUMMARY.md` - Documents execution evidence and plan outcome.

## Decisions Made

- Running truth is `loaded and heartbeat_fresh`; launchctl print is used for loaded return code and bounded crash/throttle diagnostics only.
- Plist drift is reported as its own classification based on installed plist hash versus expected plist bytes.
- Hotkey permission blockers come from the daemon heartbeat, because terminal permission probes do not prove LaunchAgent hotkey registration.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RED run failed as expected with `ImportError: cannot import name 'collect_call_control_agent_status'`.
- Existing 38-02 CLI status coverage expected launchctl PID text to mean `running: yes`; Task 2 updated that assertion to the new heartbeat-based contract.
- A non-required `python -m compileall` check hit the local pyenv shim; rerunning with `uv run python -m compileall -q saymo/analysis/launch_agent.py saymo/commands/call_control.py` passed.

## Validation Output

- `bash -lc 'uv run pytest tests/analysis/test_launch_agent.py tests/test_call_control_cli.py -q; test $? -ne 0'` - exited 0 with expected RED import error.
- `uv run pytest tests/analysis/test_launch_agent.py tests/test_call_control_cli.py -q` - `13 passed in 0.15s`.
- `uv run pytest tests/analysis/test_control_daemon.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py tests/test_hotkey_doctor.py -q` - `18 passed in 0.23s`.
- `bash -lc '! rg "bootstrap_argv\\(|bootout_argv\\(|kickstart_argv\\(|append_control_command\\(" saymo/analysis/launch_agent.py saymo/commands/call_control.py | rg "status|collect_call_control_agent_status"'` - passed with no matches.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/control_daemon.py saymo/analysis/launch_agent.py saymo/commands/call_control.py'` - passed with no matches.
- `git diff --check` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 38-04 can route explicit daemon/status actions through the existing live-control command and audit semantics. Manual macOS GUI-session verification of real LaunchAgent hotkey permission behavior remains a Phase 38 residual risk, as expected by the validation strategy.

## Self-Check: PASSED

- Created/modified files exist: `saymo/analysis/launch_agent.py`, `saymo/commands/call_control.py`, `tests/analysis/test_launch_agent.py`, `tests/test_call_control_cli.py`, and this summary.
- Task commits exist: `879ac91` and `305fceb`.

---
*Phase: 38-local-call-control-daemon-and-launchagent*
*Completed: 2026-07-08T16:10:17Z*
