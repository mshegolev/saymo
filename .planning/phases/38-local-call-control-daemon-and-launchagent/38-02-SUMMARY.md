---
phase: 38-local-call-control-daemon-and-launchagent
plan: "02"
subsystem: launchagent
tags: [live-control, launchagent, launchctl, plistlib, click, pytest]

requires:
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: foreground call-control daemon command and heartbeat model from 38-01
  - phase: 36-call-ready-preflight-and-cache-gate
    provides: shared launch-readiness constraints
  - phase: 37-provider-and-audio-remediation
    provides: non-destructive provider/audio safety baseline
provides:
  - per-profile call-control LaunchAgent plist rendering and hashing
  - launchctl argv builders for bootstrap, bootout, kickstart, and print
  - call-control-agent install, uninstall, start, stop, restart, and status CLI
affects: [phase-38, call-control-daemon, launchagent, live-control]

tech-stack:
  added: []
  patterns:
    - plistlib-rendered LaunchAgent payloads with explicit HOME/PATH/log paths
    - pure launchctl argv builders behind one injectable subprocess boundary
    - read-only status using plist/hash/plutil/launchctl print evidence

key-files:
  created:
    - saymo/analysis/launch_agent.py
    - tests/analysis/test_launch_agent.py
  modified:
    - saymo/commands/call_control.py
    - tests/test_call_control_cli.py

key-decisions:
  - "LaunchAgent labels use the generic source-safe prefix com.saymo.call-control plus a sanitized profile segment."
  - "LaunchAgent status is read-only: it checks plist existence/hash, optional plutil lint, and launchctl print without bootstrap, bootout, or kickstart."
  - "CLI lifecycle commands stay explicit mutations; tests mock the subprocess boundary so automated runs never touch real launchd."

patterns-established:
  - "LaunchAgentSpec centralizes label, plist, log, executable, environment, UID, and heartbeat interval resolution."
  - "CommandResult is the sole subprocess result shape for launchctl and plutil operations."

requirements-completed: [CTRL-01]

duration: 4min
completed: 2026-07-08T15:59:17Z
---

# Phase 38 Plan 02: LaunchAgent Lifecycle Summary

**Per-profile call-control LaunchAgent lifecycle commands backed by plistlib rendering and launchctl argv helpers**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-08T15:55:12Z
- **Completed:** 2026-07-08T15:59:17Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `saymo.analysis.launch_agent` with `LaunchAgentSpec`, plist rendering/hashing, safe label/path generation, plutil lint argv, and launchctl `bootstrap`, `bootout`, `kickstart`, and `print` argv helpers.
- Added lifecycle helpers for install, uninstall, start, stop, restart, and read-only status through one injectable `run_command()` boundary.
- Extended `saymo call-control-agent` with explicit install/uninstall/start/stop/restart/status commands while leaving the existing foreground daemon command intact.
- Added mocked unit and CLI coverage proving plistlib round-trips, safe profile paths, exact argv arrays, and no real LaunchAgent bootstrap during tests.

## Task Commits

1. **Task 1: Write RED LaunchAgent plist, argv, and CLI lifecycle tests** - `2455c07` (test)
2. **Task 2: Implement LaunchAgent lifecycle helpers and commands** - `9579b2a` (feat)

## Files Created/Modified

- `saymo/analysis/launch_agent.py` - LaunchAgent spec, plist renderer, expected hash, lifecycle helpers, status collector, and subprocess boundary.
- `saymo/commands/call_control.py` - Adds `call-control-agent` lifecycle command group.
- `tests/analysis/test_launch_agent.py` - Plistlib round-trip, safe label/path, and launchctl argv coverage.
- `tests/test_call_control_cli.py` - Mocked CLI lifecycle tests for install, uninstall, start, stop, restart, and read-only status.

## Decisions Made

- Use `com.saymo.call-control.<safe-profile>` for source-safe labels instead of any personal reverse-DNS prefix.
- Keep `status` read-only: no bootstrap, bootout, kickstart, command queue writes, provider actions, or audio actions.
- Resolve `saymo` from an explicit executable first, then `shutil.which("saymo")`; if unresolved, surface a clear CLI error instead of writing an unusable plist.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RED run failed as expected with `ModuleNotFoundError: No module named 'saymo.analysis.launch_agent'`; the wrapper command exited 0 because the selected tests failed before implementation.
- No architecture, dependency, auth, or LaunchAgent blockers.

## Validation Output

- `bash -lc 'uv run pytest tests/analysis/test_launch_agent.py tests/test_call_control_cli.py -q; test $? -ne 0'` - exited 0 with expected missing module failure.
- `uv run pytest tests/analysis/test_launch_agent.py tests/test_call_control_cli.py -q` - `7 passed in 0.13s`.
- `uv run pytest tests/analysis/test_control_daemon.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py -q` - `11 passed in 0.12s`.
- `uv run pytest tests/analysis/test_control_daemon.py tests/test_call_control_cli.py tests/analysis/test_live_control.py tests/test_live_control_cli.py tests/test_hotkey_doctor.py -q` - `15 passed in 0.21s`.
- `bash -lc '! rg "crontab|cron" saymo/analysis/launch_agent.py saymo/commands/call_control.py tests/test_call_control_cli.py'` - passed.
- `bash -lc 'rg "plistlib|LaunchAgents|launchctl|bootstrap|bootout|kickstart" saymo/analysis/launch_agent.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py'` - passed with expected matches.
- `git diff --check` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 38-03 can build daemon health diagnostics on top of `collect_launch_agent_status()`, installed plist hashes, launchctl print evidence, and the 38-01 heartbeat model.

## Self-Check: PASSED

- Created files exist: `saymo/analysis/launch_agent.py`, `tests/analysis/test_launch_agent.py`, and this summary.
- Modified files exist: `saymo/commands/call_control.py` and `tests/test_call_control_cli.py`.
- Task commits exist: `2455c07` and `9579b2a`.

---
*Phase: 38-local-call-control-daemon-and-launchagent*
*Completed: 2026-07-08T15:59:17Z*
