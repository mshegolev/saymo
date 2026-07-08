---
phase: 38-local-call-control-daemon-and-launchagent
type: context
status: ready_for_research
created: 2026-07-08
autonomous: true
requirements: [CTRL-01, CTRL-02, CTRL-03, CTRL-04, CTRL-05]
depends_on:
  - 36-call-ready-preflight-and-cache-gate
  - 37-provider-and-audio-remediation
---

# Phase 38 Context: Local Call-Control Daemon and LaunchAgent

## Goal

Keep Saymo's live-call handbrake reachable outside the terminal and prove
daemon, hotkey, heartbeat, command, and audit health before realtime mode
relies on it.

## Approved Design Direction

Use a small local control-plane daemon that reuses the existing live-control
primitives:

- `commands.jsonl` remains the durable command queue.
- `state.json` remains the operator-facing state snapshot.
- `audit.jsonl` remains the action trail consumed by scorecards and safety
  checks.
- The daemon registers global hotkeys and writes queued commands plus heartbeat
  evidence; the realtime audio/STT/TTS/provider loop continues to own
  transcription, synthesis, playback, and provider mutation.
- LaunchAgent support installs a per-profile user LaunchAgent under
  `~/Library/LaunchAgents`, with explicit `PATH`, `HOME`, stdout/stderr logs,
  and user-session `launchctl bootstrap/kickstart/bootout` commands.

This follows the repo's current macOS rule: use launchd, not cron.

## Alternatives Considered

### A. Embed More Control Into `saymo auto`

Lowest initial change, but it keeps hotkey/control availability tied to an
interactive terminal. This does not satisfy the phase goal that stop/takeover
remain reachable outside the terminal.

### B. Full Native Menu Bar App

Better operator UX later, but too much packaging/UI scope for v1.9. The daemon
and LaunchAgent contract should stabilize first.

### C. Local Control Daemon + LaunchAgent

Recommended. It preserves local-by-default behavior, reuses existing files and
tests, gives launch-readiness a concrete control-plane health signal, and keeps
mutating audio/provider behavior out of default diagnostics.

## Existing Building Blocks

- `saymo.analysis.live_control`
  - `LiveControlCommand`, `LiveControlSnapshot`
  - `append_control_command`, `read_control_commands`
  - `write_live_state`, `load_live_state`
  - `append_control_audit`
  - `effective_hotkey_bindings`, `hotkey_listener_bindings`
  - `build_hotkey_doctor_report`
- `saymo.commands.core`
  - `saymo auto` already reads the command queue and applies actions.
  - `saymo live-control-action` already queues normalized actions.
  - `saymo live-control` already opens the TUI.
- Phase 37 call-ready checks already expose provider/audio/hotkey permission
  blockers and prove default provider/audio checks are non-destructive.

## Required User-Facing Outcomes

1. CLI can install, uninstall, start, stop, restart, and inspect a per-profile
   LaunchAgent.
2. A foreground daemon command can register configured hotkeys and publish a
   fresh heartbeat/status for the selected profile.
3. Readiness/status can distinguish installed, loaded, running, stale heartbeat,
   crash-loop/log evidence, permission blockers, and plist drift.
4. Existing live-control actions can be queued through daemon/status surfaces
   with the same command semantics and audit trail as CLI/hotkeys.
5. Handbrake reachability is proven from heartbeat freshness, hotkey
   registration, command write/consume evidence, and latest applied action.

## Guardrails

- Do not create cron jobs. Use LaunchAgent plist files only.
- Default readiness/status commands must be read-only unless command names
  explicitly imply mutation: install, uninstall, start, stop, restart,
  kickstart, or action queueing.
- Do not kill Chrome, leave a meeting, switch microphones, play audio, record
  audio, transcribe, synthesize, write user config, or change macOS audio routes
  from the daemon readiness path.
- Do not move realtime audio/STT/TTS/provider ownership into the daemon.
- Keep all artifacts sanitized: no raw meeting content, transcripts, generated
  answers, audio bytes, or secrets.
- LaunchAgent labels should be stable and reverse-DNS style, e.g.
  `com.mshegolev.saymo.call-control.<profile>`.
- Treat labels and plist paths as generated from a sanitized profile only.

## Suggested Module Boundaries

- `saymo.analysis.control_daemon`
  - heartbeat/status dataclasses
  - daemon run loop primitives
  - command consumption/readiness helpers
- `saymo.analysis.launch_agent`
  - plist model/rendering
  - install/uninstall/status helpers
  - launchctl command wrappers with testable command construction
- CLI additions in `saymo.commands.core` or a focused command module:
  - `saymo call-control-daemon`
  - `saymo call-control-agent install|uninstall|start|stop|restart|status`
  - optional `saymo call-control-status`

## Validation Strategy

- Unit tests for plist rendering, labels, paths, env variables, and logs.
- Unit tests for daemon heartbeat and command/audit semantics without running a
  real LaunchAgent.
- CLI tests with mocked `launchctl` and hotkey probes.
- Static grep/tests proving daemon readiness does not perform audio/provider
  mutations.
- Manual macOS check remains required for actual LaunchAgent bootstrap in the
  user's GUI session.

## Open Design Questions Resolved by Assumption

- **Profile scope:** per-profile daemon and LaunchAgent, defaulting to
  `standup`, because current live-control files are profile-scoped.
- **Daemon lifetime:** long-running foreground process for tests/manual debug;
  LaunchAgent wraps the same command for background use.
- **Heartbeat cadence:** short interval suitable for readiness checks; exact
  default should be tuned in implementation plan and configurable/testable.
- **Command consumption:** daemon should consume command queue evidence for
  handbrake reachability, but actual realtime action application remains in
  `saymo auto` until Phase 39 explicitly gates realtime behavior.

