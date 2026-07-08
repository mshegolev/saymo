---
phase: 38-local-call-control-daemon-and-launchagent
plan: "01"
subsystem: control-daemon
tags: [live-control, daemon, heartbeat, hotkeys, click, pytest]

requires:
  - phase: 36-call-ready-preflight-and-cache-gate
    provides: shared launch readiness and remediation constraints
  - phase: 37-provider-and-audio-remediation
    provides: non-destructive provider/audio safety baseline
provides:
  - foreground call-control daemon heartbeat model
  - daemon hotkey-to-command queue integration
  - call-control-daemon CLI command with one-shot test seam
affects: [phase-38, live-control, call-control-daemon, launchagent]

tech-stack:
  added: []
  patterns:
    - profile-scoped daemon heartbeat JSON under live_control directory
    - injectable listener factory for foreground daemon tests
    - thin Click command module imported from saymo.commands.__init__

key-files:
  created:
    - saymo/analysis/control_daemon.py
    - saymo/commands/call_control.py
    - tests/analysis/test_control_daemon.py
    - tests/test_call_control_cli.py
  modified:
    - saymo/commands/__init__.py
    - tests/analysis/test_control_daemon.py

key-decisions:
  - "The foreground daemon is control-plane only: it writes heartbeat evidence and queues existing live-control commands, but does not apply realtime/audio/provider actions."
  - "Daemon hotkeys use source=daemon_hotkey so queued commands remain distinguishable from panel, CLI, and existing hotkey sources."
  - "Hotkey registration failures are recorded as blocked heartbeat status while the daemon loop keeps running."

patterns-established:
  - "ControlDaemonHeartbeat captures profile, pid, label, timestamps, hotkey status/detail, binding count, command offset, and daemon version."
  - "run_control_daemon accepts listener_factory and stop_after_heartbeats for deterministic tests without real global hotkeys."

requirements-completed: [CTRL-02]

duration: 6min
completed: 2026-07-08T15:50:52Z
---

# Phase 38 Plan 01: Foreground Call-Control Daemon Summary

**Foreground call-control daemon heartbeat and hotkey queueing through the existing live-control command log**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-08T15:45:00Z
- **Completed:** 2026-07-08T15:50:52Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `ControlDaemonHeartbeat` plus heartbeat path, write, load, and freshness helpers under the existing profile-scoped live-control directory.
- Added `run_control_daemon()` with injectable listener support, heartbeat cadence, daemon versioning, command-log offset reporting, and blocked hotkey registration status.
- Added `saymo call-control-daemon` with `--profile/-p`, `--heartbeat-interval`, `--base-dir`, `--label`, and `--once`.
- Added TDD coverage for heartbeat freshness, daemon one-shot lifecycle, daemon hotkey command queueing, registration failure survival, and CLI one-shot heartbeat evidence.

## Task Commits

1. **Task 1: Write RED daemon heartbeat and hotkey contracts** - `cb57372` (test)
2. **Task 2: Implement foreground daemon heartbeat and command registration** - `169518d` (feat)

## Files Created/Modified

- `saymo/analysis/control_daemon.py` - Foreground daemon heartbeat model, freshness helper, run loop, and daemon hotkey handlers.
- `saymo/commands/call_control.py` - Thin Click command for `call-control-daemon`.
- `saymo/commands/__init__.py` - Imports `call_control` so command decorators register.
- `tests/analysis/test_control_daemon.py` - Unit coverage for heartbeat, daemon loop, hotkey queueing, and registration failure.
- `tests/test_call_control_cli.py` - CLI one-shot daemon heartbeat coverage.

## Decisions Made

- Daemon label defaults to `com.saymo.call-control.<profile>` when no label is supplied, avoiding personal names in source.
- `no_bindings` is a non-crashing heartbeat registration status when the profile has no configured daemon hotkeys.
- The daemon queues all existing `ACTION_CATALOG` actions through `append_control_command(..., source="daemon_hotkey")`; action application stays in `saymo auto`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed duplicate fake hotkeys in RED helper**
- **Found during:** Task 2 (focused GREEN run)
- **Issue:** The RED test helper generated `<cmd>+<shift>+s` for both `stop` and `status`, so the fake binding map overwrote one callback and hid one queued command.
- **Fix:** Changed the helper to use the real default unique hotkeys for each action.
- **Files modified:** `tests/analysis/test_control_daemon.py`
- **Verification:** `uv run pytest tests/analysis/test_control_daemon.py tests/test_call_control_cli.py -q` passed.
- **Committed in:** `169518d`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** Test helper correction only; production scope remained exactly within the daemon and CLI contract.

## Issues Encountered

- Initial RED run failed as expected with `ModuleNotFoundError: No module named 'saymo.analysis.control_daemon'`; wrapper command exited 0 because tests failed before implementation.
- No architecture, dependency, auth, or LaunchAgent blockers.

## Validation Output

- `bash -lc 'uv run pytest tests/analysis/test_control_daemon.py tests/test_call_control_cli.py -q; test $? -ne 0'` - exited 0 with expected missing module failure.
- `uv run pytest tests/analysis/test_control_daemon.py tests/test_call_control_cli.py -q` - `5 passed in 0.12s`.
- `uv run pytest tests/analysis/test_live_control.py tests/test_live_control_cli.py tests/test_hotkey_doctor.py tests/test_auto_qa_flow.py -q` - `46 passed in 0.32s`.
- `uv run pytest tests/analysis/test_control_daemon.py tests/test_call_control_cli.py tests/analysis/test_live_control.py tests/test_live_control_cli.py tests/test_hotkey_doctor.py -q` - `12 passed in 0.23s`.
- `uv run pytest` - `448 passed in 5.29s`.
- Static non-destructive grep for provider/audio/recording/config/kill APIs in `control_daemon.py` and `call_control.py` passed.
- Static `crontab|cron` grep in `call_control.py` and `tests/test_call_control_cli.py` passed.
- `git diff --check` passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 38-02 can wrap the same foreground `saymo call-control-daemon` command in a per-profile user LaunchAgent. The daemon heartbeat file and blocked hotkey status are available for later status/readiness rows.

## Self-Check: PASSED

- Created files exist: `saymo/analysis/control_daemon.py`, `saymo/commands/call_control.py`, `tests/analysis/test_control_daemon.py`, `tests/test_call_control_cli.py`, and this summary.
- Task commits exist: `cb57372` and `169518d`.

---
*Phase: 38-local-call-control-daemon-and-launchagent*
*Completed: 2026-07-08T15:50:52Z*
