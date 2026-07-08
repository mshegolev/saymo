---
phase: 38-local-call-control-daemon-and-launchagent
verified: 2026-07-08T16:40:55Z
status: passed
score: 5/5 must-haves verified
re_verification: false
residual_risks:
  - risk: "Real macOS GUI-session LaunchAgent/TCC behavior still needs a manual smoke check on the user's machine."
    blocks_phase: false
    reason: "Automated contracts mock launchctl/hotkeys, and docs include the required GUI-session smoke check."
---

# Phase 38: Local Call-Control Daemon and LaunchAgent Verification Report

**Phase Goal:** User can keep the live-call handbrake reachable outside the terminal and prove daemon, hotkey, heartbeat, command, and audit health before realtime mode relies on it.
**Verified:** 2026-07-08T16:40:55Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

Phase 38 is achieved. The codebase now has a foreground control daemon, per-profile LaunchAgent lifecycle, heartbeat-based status diagnostics, existing `commands.jsonl`/`audit.jsonl` action semantics, an explicit reachability probe, and read-only `call-ready` daemon rows. The only remaining verification item is a real macOS GUI-session LaunchAgent/TCC smoke check, which is documented and does not block Phase 38 because the automated contracts pass.

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | User can install, uninstall, start, stop, restart, and inspect a per-profile call-control LaunchAgent. | VERIFIED | `call-control-agent` CLI commands exist in `saymo/commands/call_control.py:150`; plist/paths/env are rendered in `saymo/analysis/launch_agent.py:99`; lifecycle helpers use `bootstrap`, `bootout`, `kickstart`, and status in `saymo/analysis/launch_agent.py:225`. |
| 2 | A foreground daemon registers configured global hotkeys and publishes fresh heartbeat/status. | VERIFIED | Heartbeat model includes profile, pid, label, timestamps, hotkey status, binding count, offset, and version in `saymo/analysis/control_daemon.py:30`; daemon registers `hotkey_listener_bindings` and writes heartbeats in `saymo/analysis/control_daemon.py:241`; hotkey callbacks queue commands at `saymo/analysis/control_daemon.py:322`. |
| 3 | Diagnostics distinguish installed, loaded, running, stale, crash-loop, permission, and plist drift, using heartbeat freshness as running truth. | VERIFIED | `collect_call_control_agent_status()` reads plist/hash, plutil, launchctl print, heartbeat, and hotkey status in `saymo/analysis/launch_agent.py:282`; running is `loaded and heartbeat_fresh` at `saymo/analysis/launch_agent.py:348`; classifications are implemented in `saymo/analysis/launch_agent.py:457`. |
| 4 | Daemon/status actions reuse existing command queue and audit semantics with correlation and duplicate-hotkey prevention seam. | VERIFIED | Existing `append_control_command()` and sanitized payload shape remain in `saymo/analysis/live_control.py:205`; audit accepts optional `command_id`/`probe_id` in `saymo/analysis/live_control.py:311`; `call-control action` queues normalized existing actions in `saymo/commands/call_control.py:81`; auto preserves command metadata in `saymo/commands/core.py:224` and consumes queued commands in `saymo/commands/core.py:653`; trusted-daemon hotkey skip seam is at `saymo/commands/core.py:608`. |
| 5 | Explicit probe proves heartbeat, hotkey, command write, command consumption, and audit evidence; call-ready has read-only rows and grouped remediation. | VERIFIED | `run_handbrake_reachability_probe()` queues a benign `status` command and requires heartbeat, hotkeys, command offset, and matching audit in `saymo/analysis/control_daemon.py:141`; CLI probe is in `saymo/commands/call_control.py:118`; `call-ready` appends `call_control_agent`, `call_control_daemon`, and `call_control_hotkeys` read-only rows in `saymo/analysis/launch_readiness.py:256`; remediation categories are covered by `saymo/analysis/remediation.py:52` and key mapping in `saymo/analysis/remediation.py:292`. |

**Score:** 5/5 truths verified

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| CTRL-01 | CLI lifecycle install/uninstall/start/stop/restart/status per-profile LaunchAgent, plistlib, launchd not cron. | SATISFIED | `LaunchAgentSpec`, `plistlib.dumps`, `~/Library/LaunchAgents`, explicit env/log paths, and launchctl argv helpers in `saymo/analysis/launch_agent.py:99`; CLI commands in `saymo/commands/call_control.py:150`; tests in `tests/analysis/test_launch_agent.py` and `tests/test_call_control_cli.py`; static cron guard passed. |
| CTRL-02 | Foreground daemon registers configured hotkeys and writes fresh heartbeat/status. | SATISFIED | `run_control_daemon()` uses existing `hotkey_listener_bindings`, keeps running on registration failure, and writes heartbeat in `saymo/analysis/control_daemon.py:241`; tests cover fresh heartbeat, queueing, and blocked registration in `tests/analysis/test_control_daemon.py`. |
| CTRL-03 | Diagnostics distinguish installed/loaded/running/stale/crash-loop/permission/plist drift and use heartbeat freshness as running truth. | SATISFIED | `CallControlAgentStatus` fields in `saymo/analysis/launch_agent.py:72`; status aggregation and heartbeat-based running in `saymo/analysis/launch_agent.py:282`; classifications in `saymo/analysis/launch_agent.py:457`; tests cover all classifications in `tests/analysis/test_launch_agent.py`. |
| CTRL-04 | Daemon/CLI actions reuse `commands.jsonl` and audit semantics; command_id/probe_id preserved; duplicate local hotkey prevention seam exists. | SATISFIED | `append_control_command`, `read_control_commands`, and `append_control_audit` in `saymo/analysis/live_control.py:205`; `daemon_cli`/`daemon_hotkey` paths in `saymo/commands/call_control.py:81` and `saymo/analysis/control_daemon.py:322`; auto audit and local hotkey disable seam in `saymo/commands/core.py:224` and `saymo/commands/core.py:608`; tests in `tests/test_auto_qa_flow.py` and `tests/analysis/test_live_control.py`. |
| CTRL-05 | Explicit probe proves heartbeat, hotkey, command write/consume, and audit; call-ready has read-only rows and grouped remediation. | SATISFIED | Probe logic in `saymo/analysis/control_daemon.py:141`; call-ready rows in `saymo/analysis/launch_readiness.py:256`; tests prove default call-ready does not run probe in `tests/test_call_ready_cli.py`; docs include LaunchAgent, probe, logs, Accessibility, and GUI smoke at `docs/LIVE-CONTROL-HANDBRAKE.md:20` and `docs/LIVE-CONTROL-HANDBRAKE.md:93`. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `saymo/analysis/control_daemon.py` | Daemon heartbeat, hotkey queueing, explicit probe. | VERIFIED | Substantive implementation; wired to live-control command/audit files and CLI. |
| `saymo/analysis/launch_agent.py` | LaunchAgent spec/plist/lifecycle/status. | VERIFIED | Uses `plistlib`, `/bin/launchctl`, `/usr/bin/plutil`, GUI domain argv, heartbeat status. |
| `saymo/analysis/live_control.py` | Existing command/audit semantics with correlation fields. | VERIFIED | `commands.jsonl`, `audit.jsonl`, command ids, sanitized `probe_id` preserved. |
| `saymo/analysis/launch_readiness.py` | Read-only call-control rows in `call-ready`. | VERIFIED | Appends agent/daemon/hotkey rows after provider/audio checks. |
| `saymo/analysis/remediation.py` | Grouped call-control/macOS permission remediation. | VERIFIED | Launch readiness hint mapping covers call-control rows. |
| `saymo/commands/call_control.py` | CLI daemon, action, probe, and agent lifecycle commands. | VERIFIED | Thin CLI wrappers delegate to analysis helpers. |
| `saymo/commands/core.py` | Auto command-loop audit correlation and duplicate-hotkey seam. | VERIFIED | Consumes queued commands and preserves command context into audit. |
| `docs/LIVE-CONTROL-HANDBRAKE.md` | Operator guide for LaunchAgent/status/probe/logs/Accessibility/manual smoke. | VERIFIED | Documents LaunchAgent flow, control-plane-only daemon, logs, and residual manual smoke. |
| Listed tests | Automated regression coverage. | VERIFIED | Focused Phase 38 suite, safety regression suite, and full suite pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `call_control.py` | `control_daemon.run_control_daemon` | `call-control-daemon` | WIRED | Foreground daemon command delegates directly. |
| `call_control.py` | `launch_agent` lifecycle/status helpers | `call-control-agent` group | WIRED | Install/uninstall/start/stop/restart/status commands delegate to helper functions. |
| `control_daemon.py` | `live_control.append_control_command` | daemon hotkeys and probe | WIRED | Daemon hotkeys use `source="daemon_hotkey"`; probe uses `source="probe"`. |
| `core.py` | `live_control.read_control_commands` and audit | auto command loop | WIRED | Queued commands are applied and audited with command/probe ids. |
| `launch_readiness.py` | `launch_agent.collect_call_control_agent_status` | call-ready rows | WIRED | Default readiness reads status only; probe is not invoked. |
| `remediation.py` | launch readiness rows | grouped remediation | WIRED | Call-control rows map to `call-control` or `macos-permission`. |

### Safety And Anti-Patterns

| Check | Status | Evidence |
|---|---|---|
| No default status/readiness path mutates provider/audio/config/Chrome. | PASSED | Static destructive-call guard returned no matches; CLI tests assert provider/audio methods and probe mutation are not called by default `call-ready`. |
| No cron usage. | PASSED | Static guard found no `cron`/`crontab` in docs or Phase 38 launch/control files. |
| Artifacts/docs sanitized. | PASSED | Sanitizers redact known private/token sentinels; production grep only found sentinel definitions in `launch_readiness.py`; docs contain paths/commands only. |
| Stub/placeholder scan. | PASSED | Matches were legitimate empty-return helpers and tests for placeholder daily-note blockers; no blocker stubs found. |

### Residual Risks

| Risk | Blocks Phase 38? | Reason |
|---|---|---|
| Real LaunchAgent behavior in the user's macOS GUI session, including launchd environment and TCC Accessibility identity, still requires manual smoke testing. | No | The phase contract is implemented and covered by mocked launchctl/hotkey tests. The docs explicitly require `install`, `start`, `status`, `call-ready`, `launchctl print`, and `probe` from the GUI session before relying on the background handbrake. |

### Verification Commands And Outputs

```bash
for f in .planning/phases/38-local-call-control-daemon-and-launchagent/*-VERIFICATION.md(N); do sed -n '1,260p' "$f"; done
```

Output: no output; no previous verification report existed.

```bash
node /Users/m.v.shchegolev/.codex/get-shit-done/bin/gsd-tools.cjs verify artifacts .planning/phases/38-local-call-control-daemon-and-launchagent/38-01-PLAN.md
```

Output:
```json
{
  "error": "No must_haves.artifacts found in frontmatter",
  "path": ".planning/phases/38-local-call-control-daemon-and-launchagent/38-01-PLAN.md"
}
```

Same output shape occurred for `38-02-PLAN.md` through `38-05-PLAN.md`, so artifact verification was performed manually against the plan frontmatter and code.

```bash
uv run pytest tests/analysis/test_control_daemon.py tests/analysis/test_launch_agent.py tests/analysis/test_launch_readiness.py tests/analysis/test_remediation.py tests/test_call_control_cli.py tests/test_live_control_cli.py tests/test_hotkey_doctor.py -q
```

Output:
```text
.......................................                                  [100%]
39 passed in 1.30s
```

```bash
uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py -q
```

Output:
```text
.....................................................                    [100%]
53 passed in 1.30s
```

```bash
uv run pytest
```

Output excerpt:
```text
collected 473 items
...
============================= 473 passed in 5.46s ==============================
```

```bash
if rg "activate_meeting\(|toggle_mute\(|switch_mic\(|get_previous_app\(|activate_app\(|leave_meeting\(|play_audio_bytes|play_bytes_to_devices|sd\.rec|sounddevice\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/control_daemon.py saymo/analysis/launch_agent.py saymo/analysis/launch_readiness.py saymo/commands/call_control.py saymo/commands/call_ready.py; then exit 1; else echo "no destructive provider/audio/config/process calls found"; fi
```

Output:
```text
no destructive provider/audio/config/process calls found
```

```bash
if rg "crontab|cron" docs/LIVE-CONTROL-HANDBRAKE.md saymo/analysis/launch_agent.py saymo/commands/call_control.py tests/test_call_control_cli.py; then exit 1; else echo "no cron references found in docs or Phase 38 launch/control files"; fi
```

Output:
```text
no cron references found in docs or Phase 38 launch/control files
```

```bash
rg "plistlib|LaunchAgents|launchctl|bootstrap|bootout|kickstart" saymo/analysis/launch_agent.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py
```

Output: expected matches found in `launch_agent.py`, `tests/analysis/test_launch_agent.py`, and `tests/test_call_control_cli.py` for plistlib, `LaunchAgents`, `/bin/launchctl`, `bootstrap`, `bootout`, and `kickstart`.

```bash
git diff --check
```

Output: no output.

## Gaps Summary

No blocking gaps found. All CTRL-01 through CTRL-05 requirements are satisfied by code, tests, static guards, and docs. Manual macOS GUI-session LaunchAgent smoke remains a documented operational check before relying on the background handbrake in a real call.

---

_Verified: 2026-07-08T16:40:55Z_
_Verifier: Claude (gsd-verifier)_
