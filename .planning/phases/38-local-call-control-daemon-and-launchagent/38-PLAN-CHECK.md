---
phase: 38-local-call-control-daemon-and-launchagent
type: plan-check
status: pass
created: 2026-07-08
requirements: [CTRL-01, CTRL-02, CTRL-03, CTRL-04, CTRL-05]
plans_checked:
  - 38-01-PLAN.md
  - 38-02-PLAN.md
  - 38-03-PLAN.md
  - 38-04-PLAN.md
  - 38-05-PLAN.md
---

# Phase 38 Plan Check: PASS

## Verdict

PASS. The five plans are goal-backward complete for Phase 38 and can proceed to
execution.

## Requirement Coverage

| Requirement | Covering plans | Status |
|-------------|----------------|--------|
| CTRL-01 LaunchAgent lifecycle CLI | 38-02, 38-05 | Covered |
| CTRL-02 foreground daemon, hotkeys, heartbeat | 38-01, 38-05 | Covered |
| CTRL-03 installed/loaded/running/stale/crash/permission/plist drift status | 38-03, 38-05 | Covered |
| CTRL-04 existing action queue and audit semantics | 38-04, 38-05 | Covered |
| CTRL-05 pre-call handbrake reachability proof | 38-05 | Covered |

The plans collectively prove the phase goal: LaunchAgent management, foreground
daemon health, status diagnostics, action/audit compatibility, and explicit
reachability proof are all represented by concrete tasks, files, verification
commands, and done criteria.

## Specific Checks

1. CTRL-01..CTRL-05 are covered.
   - Each roadmap requirement appears in plan frontmatter.
   - Plan 38-05 reclaims all CTRL requirements for final integration and full
     validation.

2. Dependencies and file ownership are safe for sequential execution.
   - Waves are linear: 38-01 -> 38-02 -> 38-03 -> 38-04 -> 38-05.
   - Shared files are extended only after their owning foundation plan runs.
   - `tests/test_call_control_cli.py` is created first, then extended in later
     waves.

3. The daemon remains control-plane-only.
   - Plans explicitly prohibit audio recording/playback, mic switching,
     provider mutation, config writes, Chrome kill commands, and realtime-loop
     ownership in daemon/status/readiness/probe paths.
   - Static guards cover `control_daemon.py`, `launch_agent.py`,
     `launch_readiness.py`, `call_control.py`, and `call_ready.py`.

4. LaunchAgent design uses launchd, not cron.
   - Plan 38-02 owns `plistlib` rendering, `~/Library/LaunchAgents`, explicit
     `HOME`/`PATH`, stdout/stderr logs, and list-argv `launchctl` helpers for
     `bootstrap`, `bootout`, `kickstart`, and `print`.
   - Tests mock `launchctl` and check argv construction; they do not bootstrap a
     real LaunchAgent.

5. Plan 38-05 integrates daemon readiness into `call-ready`.
   - It adds `call_control_agent`, `call_control_daemon`, and
     `call_control_hotkeys` readiness rows after provider/audio checks.
   - It extends remediation categories for missing/stale/crashing daemon,
     Accessibility blockers, and explicit `saymo call-control probe` reruns.
   - Default `call-ready` remains read-only and must not queue a probe.

6. Duplicate hotkey listeners are addressed.
   - Plan 38-04 adds tests and an implementation seam so trusted daemon controls
     can disable `saymo auto` local hotkey registration.
   - Default auto-mode behavior is preserved until the trusted daemon path opts
     in, matching Phase 39's later realtime gating boundary.

7. Command/audit correlation and reachability probe tests are sufficient.
   - Plan 38-04 tests `command_id` and sanitized `probe_id` propagation from
     queued commands into audit events.
   - Plan 38-05 tests heartbeat freshness, hotkey registration, command write,
     command consumption, matching audit evidence, stale heartbeat, blocked
     hotkeys, written-not-consumed, and missing-audit failure modes.

## Plan Structure

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 38-01 | 1 | 2 | 5 | CTRL-02 | Valid |
| 38-02 | 2 | 2 | 4 | CTRL-01 | Valid |
| 38-03 | 3 | 2 | 6 | CTRL-03 | Valid |
| 38-04 | 4 | 2 | 9 | CTRL-04 | Valid |
| 38-05 | 5 | 2 | 13 | CTRL-01..CTRL-05 | Valid |

Plan 38-05 is broad, but acceptable as the final integration wave: earlier
plans isolate daemon, LaunchAgent, status, and audit semantics first, and the
final plan carries focused, safety, static, launchd-not-cron, and full-suite
validation.

## Nyquist Compliance

VALIDATION.md exists and RESEARCH.md contains a Validation Architecture section.
Every implementation task has an automated verify command. No watch mode,
missing automated command, or Wave 0 linkage gap was found.

| Plan | Task 1 automated verify | Task 2 automated verify | Status |
|------|-------------------------|-------------------------|--------|
| 38-01 | RED pytest command | daemon/live-control pytest plus safety grep | PASS |
| 38-02 | RED pytest command | launch-agent pytest plus launchd-not-cron grep | PASS |
| 38-03 | RED pytest command | status pytest plus read-only and safety grep | PASS |
| 38-04 | RED pytest command | action/audit pytest plus safety grep | PASS |
| 38-05 | RED pytest command | focused, safety, full suite, static guards | PASS |

Sampling continuity passes: each wave contains two implementation tasks, and
both tasks in every wave have automated verification.

## Context Compliance

The plans honor the locked context decisions:

- `commands.jsonl`, `state.json`, and `audit.jsonl` remain the durable control
  contract.
- The daemon registers hotkeys, writes heartbeat evidence, and queues existing
  commands.
- Realtime audio/STT/TTS/provider mutation stays in the existing realtime loop.
- LaunchAgent lifecycle uses per-profile user LaunchAgents, not cron.
- Readiness/status defaults remain read-only except explicit lifecycle/action
  and probe commands.

No deferred/out-of-scope item is planned: no native menu bar app, socket/XPC
protocol, provider repair, audio route mutation, realtime fail-closed gating,
scorecard evidence work, or safety-soak v1.9 work is included in Phase 38.

## Execution Recommendation

Proceed with `/gsd:execute-phase 38`.
