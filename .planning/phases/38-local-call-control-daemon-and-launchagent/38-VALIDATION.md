---
phase: 38-local-call-control-daemon-and-launchagent
type: validation
status: ready_for_planning
created: 2026-07-08
requirements: [CTRL-01, CTRL-02, CTRL-03, CTRL-04, CTRL-05]
---

# Phase 38 Validation Strategy

## Goal-Backward Truths

Phase 38 is complete only when all of these are true:

1. A user can manage a per-profile Saymo call-control LaunchAgent from CLI:
   install, uninstall, start, stop, restart, and status.
2. A foreground daemon can register configured hotkeys, publish heartbeat
   evidence, and expose status without requiring a focused terminal window.
3. Readiness/status distinguishes installed, loaded, running, stale heartbeat,
   crash-loop/log evidence, permission blockers, and expected-plist drift.
4. Daemon hotkeys and explicit action commands queue existing live-control
   actions through `commands.jsonl` and preserve the existing audit semantics.
5. A pre-call reachability probe can prove heartbeat freshness, hotkey
   registration, command write, command consumption, and latest applied action
   evidence without provider/audio mutations.

## Automated Validation Commands

### Focused Phase 38 Suite

```bash
uv run pytest \
  tests/analysis/test_control_daemon.py \
  tests/analysis/test_launch_agent.py \
  tests/analysis/test_launch_readiness.py \
  tests/analysis/test_remediation.py \
  tests/test_call_control_cli.py \
  tests/test_live_control_cli.py \
  tests/test_hotkey_doctor.py \
  -q
```

### Safety Regression Suite

```bash
uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py -q
```

### Full Suite

```bash
uv run pytest
```

### Static Non-Destructive Guard

```bash
! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" \
  saymo/analysis/control_daemon.py \
  saymo/analysis/launch_agent.py \
  saymo/analysis/launch_readiness.py \
  saymo/commands/call_control.py \
  saymo/commands/call_ready.py
```

### LaunchAgent Safety Guard

```bash
! rg "crontab|cron" saymo/analysis/launch_agent.py saymo/commands/call_control.py tests/test_call_control_cli.py
rg "plistlib|LaunchAgents|launchctl|bootstrap|bootout|kickstart" \
  saymo/analysis/launch_agent.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py
```

## Required Test Coverage

### CTRL-01: LaunchAgent Lifecycle

- Plist rendering uses `plistlib`, stable reverse-DNS labels, explicit `PATH`
  and `HOME`, `ProgramArguments`, `RunAtLoad`, `KeepAlive`, stdout/stderr logs,
  and per-profile safe paths.
- CLI tests mock filesystem and `launchctl` command runners for install,
  uninstall, start, stop, restart, and status.
- Status output exposes expected plist path, loaded/running state, log paths,
  and next action.

### CTRL-02: Foreground Daemon and Heartbeat

- Daemon writes `daemon-heartbeat.json` periodically with profile, pid,
  started_at, heartbeat_at, hotkey status, command offset, and daemon version.
- Hotkey registration uses existing `effective_hotkey_bindings` /
  `hotkey_listener_bindings` semantics.
- Foreground daemon tests use an injectable listener factory and stop condition;
  they do not create a real long-running process.

### CTRL-03: Health Diagnostics

- Status/readiness classifies:
  - not installed
  - installed but not loaded
  - loaded with fresh heartbeat
  - stale heartbeat
  - crash-loop or non-zero last exit evidence
  - hotkey/Accessibility blocked
  - plist drift from expected rendered config
- Diagnostics include remediation actions and rerun commands.

### CTRL-04: Command and Audit Semantics

- Daemon hotkey handlers call `append_control_command()` with normalized
  actions and source metadata such as `daemon-hotkey`.
- Existing `live-control-action` behavior remains unchanged.
- Any added audit/probe fields stay sanitized and compatible with existing
  scorecard parsing.

### CTRL-05: Reachability Probe

- Probe writes a command with a unique probe id.
- Probe can detect command consumption from command-log offset/heartbeat
  evidence.
- Probe can detect latest applied action from audit entries when `saymo auto`
  has consumed the command.
- Failure modes are explicit and do not mutate provider, audio, config, or
  system routes.

## Manual macOS Verification

Automated tests mock `launchctl` and hotkey listeners. Before relying on a
real machine, run these manually in the user's GUI session:

```bash
uv run saymo call-control-agent install -p standup
uv run saymo call-control-agent start -p standup
uv run saymo call-control-agent status -p standup
uv run saymo call-ready -p standup --provider glip
launchctl print gui/$(id -u)/com.mshegolev.saymo.call-control.standup
```

Expected:

- LaunchAgent is loaded in the user GUI domain.
- Heartbeat is fresh.
- Hotkey registration is `ok` or reports an actionable Accessibility blocker.
- Logs are written under `~/.saymo/live_control/standup/logs/`.

## Done Criteria

- Phase 38 focused suite passes.
- Full suite passes.
- Static non-destructive and launchd-not-cron greps pass.
- `call-ready` includes daemon/control readiness rows with grouped
  remediation.
- `38-VERIFICATION.md` marks CTRL-01 through CTRL-05 as verified or documents
  any manual macOS residual risk as non-blocking.

