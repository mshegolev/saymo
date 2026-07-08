---
phase: 38-local-call-control-daemon-and-launchagent
plan: "05"
subsystem: handbrake-reachability
tags: [live-control, call-control, launchagent, heartbeat, probe, call-ready, pytest]

requires:
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: foreground daemon heartbeat, LaunchAgent status, and audit correlation from 38-01 through 38-04
  - phase: 37-provider-and-audio-remediation
    provides: provider/audio non-destructive safety baseline and permission remediation rows
provides:
  - explicit handbrake reachability probe with heartbeat, hotkey, command, and audit evidence
  - call-ready call-control agent, daemon, and hotkey readiness rows
  - call-control remediation categories and LaunchAgent operator docs
affects: [phase-38, phase-39, call-ready, realtime-gating, live-control]

tech-stack:
  added: []
  patterns:
    - explicit probe command is the only call-control readiness path allowed to queue a command
    - default call-ready appends read-only daemon rows after provider/audio rows
    - probe evidence uses existing status action with source=probe and sanitized probe_id

key-files:
  created:
    - .planning/phases/38-local-call-control-daemon-and-launchagent/38-05-SUMMARY.md
  modified:
    - saymo/analysis/control_daemon.py
    - saymo/analysis/launch_readiness.py
    - saymo/analysis/remediation.py
    - saymo/commands/call_control.py
    - docs/LIVE-CONTROL-HANDBRAKE.md
    - tests/analysis/test_control_daemon.py
    - tests/analysis/test_launch_readiness.py
    - tests/analysis/test_remediation.py
    - tests/test_call_control_cli.py
    - tests/test_call_ready_cli.py
    - tests/test_live_control_docs.py

key-decisions:
  - "The reachability probe uses the existing benign status action with source=probe and sanitized probe_id instead of adding a new live-control action."
  - "Default call-ready remains read-only: it reports call-control agent, daemon, and hotkey status but never queues the explicit probe."
  - "Call-control daemon readiness rows block launch readiness and carry log paths so Phase 39 can require handbrake evidence before realtime mode."

patterns-established:
  - "HandbrakeReachabilityProbe reports separate heartbeat_fresh, hotkeys_active, command_written, command_consumed, and audit_applied booleans."
  - "Call-control readiness rows use metadata.category=call-control except blocked hotkey registration maps to macos-permission."
  - "Operator docs treat LaunchAgent verification as a macOS GUI-session smoke check and keep the daemon control-plane only."

requirements-completed: [CTRL-01, CTRL-02, CTRL-03, CTRL-04, CTRL-05]

duration: 7min
completed: 2026-07-08T16:32:08Z
---

# Phase 38 Plan 05: Handbrake Reachability Probe Summary

**End-to-end handbrake reachability proof using daemon heartbeat, status command consumption, matching audit evidence, call-ready rows, and LaunchAgent docs**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-08T16:25:19Z
- **Completed:** 2026-07-08T16:32:08Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Added `HandbrakeReachabilityProbe` and `run_handbrake_reachability_probe()` using existing `commands.jsonl`, heartbeat offset evidence, and matching `audit.jsonl` correlation.
- Added `saymo call-control probe -p/--profile --base-dir --timeout --json`; it exits 0 only when heartbeat, hotkeys, command write, command consumption, and audit evidence all pass.
- Appended read-only `call_control_agent`, `call_control_daemon`, and `call_control_hotkeys` rows to `saymo call-ready` after provider/audio checks, including plist/log paths and remediation metadata.
- Extended remediation and docs with LaunchAgent lifecycle, status/probe commands, Accessibility guidance, GUI-session smoke check, logs, and the control-plane-only guardrail.
- Added static safety coverage proving daemon/status/readiness code does not call provider mutators, audio playback/recording, config writes, route/volume mutation, or process kill commands.

## Task Commits

1. **Task 1: Write RED probe, call-ready, remediation, docs, and safety tests** - `dd1a5c3` (test)
2. **Task 2: Implement reachability probe, call-ready integration, docs, and final validation** - `f138415` (feat)

## Files Created/Modified

- `saymo/analysis/control_daemon.py` - Adds reachability probe dataclass, probe command queueing, heartbeat/command/audit polling, and sanitized log path reporting.
- `saymo/analysis/launch_readiness.py` - Appends call-control agent, daemon, and hotkey rows to the shared call-ready report.
- `saymo/analysis/remediation.py` - Maps call-control rows to `call-control` or `macos-permission` categories.
- `saymo/commands/call_control.py` - Adds `saymo call-control probe` human and JSON output.
- `docs/LIVE-CONTROL-HANDBRAKE.md` - Documents LaunchAgent lifecycle, status/probe flow, logs, Accessibility, GUI-session check, and control-plane-only scope.
- `tests/analysis/test_control_daemon.py` - Covers full probe proof plus stale heartbeat, hotkey blocked, command-not-consumed, and missing-audit failures.
- `tests/analysis/test_launch_readiness.py` - Covers daemon row ordering, metadata, reruns, and hotkey permission category.
- `tests/analysis/test_remediation.py` - Covers call-control and Accessibility remediation actions.
- `tests/test_call_control_cli.py` - Covers probe JSON and human failure output with log paths.
- `tests/test_call_ready_cli.py` - Covers daemon rows in JSON/artifacts and proves default call-ready does not run the probe.
- `tests/test_live_control_docs.py` - Covers LaunchAgent/probe docs and static non-destructive guardrails.

## Decisions Made

- Use `status` as the probe action so no new live-control action name or protocol was introduced.
- Treat command consumption as daemon heartbeat command-log offset reaching the post-write offset, and treat audit application as a matching `probe_id` plus `command_id` audit entry.
- Keep `saymo call-ready` non-mutating; users must run `saymo call-control probe -p <profile>` explicitly to queue proof traffic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed call-ready artifact test ordering around conditional permission rows**
- **Found during:** Task 2 focused GREEN run
- **Issue:** The RED artifact test assumed call-control rows immediately followed provider/audio rows, but conditional permission rows are also provider/audio readiness rows and can appear before call-control rows.
- **Fix:** Updated the assertion to require call-control rows after all provider/audio and permission rows while preserving their internal order.
- **Files modified:** `tests/test_call_ready_cli.py`
- **Verification:** Focused suite rerun passed: `41 passed in 2.03s`.
- **Committed in:** `f138415`

**2. [Rule 1 - Bug] Fixed probe polling freshness timestamp**
- **Found during:** Task 2 diff review
- **Issue:** Probe polling initially reused the start timestamp for every heartbeat freshness check, which could classify a heartbeat written during polling as a future timestamp.
- **Fix:** Recompute current time on each poll unless the test injects `now=...`.
- **Files modified:** `saymo/analysis/control_daemon.py`
- **Verification:** `uv run pytest tests/analysis/test_control_daemon.py tests/test_call_control_cli.py -q` passed with `14 passed in 0.26s`, followed by all required suites.
- **Committed in:** `f138415`

---

**Total deviations:** 2 auto-fixed (Rule 1 bugs)
**Impact on plan:** Both fixes were directly tied to the planned contracts. No architecture or scope changes.

## Issues Encountered

- RED verification failed as expected with `ImportError: cannot import name 'run_handbrake_reachability_probe'`; wrapper command exited 0 because tests failed before implementation.
- Focused GREEN initially had one test assertion failure due conditional permission row ordering; fixed as documented above.
- Manual macOS GUI-session LaunchAgent smoke testing remains outside automated execution and is documented in the operator guide.

## Validation Output

- `bash -lc 'uv run pytest tests/analysis/test_control_daemon.py tests/analysis/test_launch_readiness.py tests/analysis/test_remediation.py tests/test_call_control_cli.py tests/test_call_ready_cli.py tests/test_live_control_docs.py -q; test $? -ne 0'` - exited 0 with expected RED import failure.
- `uv run pytest tests/analysis/test_control_daemon.py tests/analysis/test_launch_readiness.py tests/analysis/test_remediation.py tests/test_call_control_cli.py tests/test_call_ready_cli.py tests/test_live_control_docs.py -q` - `41 passed in 2.03s`.
- `uv run pytest tests/analysis/test_control_daemon.py tests/analysis/test_launch_agent.py tests/analysis/test_launch_readiness.py tests/analysis/test_remediation.py tests/test_call_control_cli.py tests/test_live_control_cli.py tests/test_hotkey_doctor.py -q` - `39 passed in 1.24s`.
- `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py -q` - `53 passed in 1.33s`.
- `uv run pytest` - `473 passed in 5.35s`.
- Static non-destructive grep for provider/audio/recording/config/kill APIs passed.
- Static `crontab|cron` grep in LaunchAgent/call-control files passed.
- LaunchAgent evidence grep for `plistlib|LaunchAgents|launchctl|bootstrap|bootout|kickstart` passed with expected matches.
- `git diff --check` passed.

## User Setup Required

None - no external service configuration required.

Manual macOS GUI-session verification is still recommended before relying on the background handbrake:

```bash
saymo call-control-agent install -p standup
saymo call-control-agent start -p standup
saymo call-control-agent status -p standup
saymo call-control probe -p standup
```

## Next Phase Readiness

Phase 38 now covers CTRL-01 through CTRL-05. Phase 39 can use call-ready daemon rows and the explicit probe as prerequisites for fail-closed realtime startup without moving provider/audio/TTS ownership into the daemon.

## Self-Check: PASSED

- Created/modified files exist: `saymo/analysis/control_daemon.py`, `saymo/analysis/launch_readiness.py`, `saymo/analysis/remediation.py`, `saymo/commands/call_control.py`, `docs/LIVE-CONTROL-HANDBRAKE.md`, test files, and this summary.
- Task commits exist: `dd1a5c3` and `f138415`.
- `git diff --check` passed after summary creation.

---
*Phase: 38-local-call-control-daemon-and-launchagent*
*Completed: 2026-07-08T16:32:08Z*
