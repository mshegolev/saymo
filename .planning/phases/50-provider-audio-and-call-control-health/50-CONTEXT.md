# Phase 50: Provider, Audio, And Call-Control Health - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase hardens the provider, Chrome tab, BlackHole routing, playback/capture
device, macOS permission, call-control daemon, and LaunchAgent checks already
included in launch readiness. It should make `saymo dry-run` prove these
environment checks clearly before a real call, while every repair remains an
explicit operator command.

</domain>

<decisions>
## Implementation Decisions

### Provider And Chrome Readiness
- Keep provider checks read-only: verify configured provider, Chrome/provider
  state, meeting-tab readiness, provider capabilities, and permission-like
  failures without activating tabs, toggling mute, or switching microphones.
- Dry-run provider actions should name the exact manual step or diagnostic
  command, such as opening the Glip meeting tab in Chrome, running
  `saymo provider-latency`, or rerunning `saymo dry-run -p <profile> --provider <provider>`.
- Surface provider metadata that helps debugging: configured provider,
  resolved provider name, URL pattern, app-running state, meeting-found state,
  tab info, and sanitized error type.
- Preserve current call-ready behavior where it is already used by older tests,
  but dry-run output should be dry-run-labelled and operator-friendly.

### Audio Routing Readiness
- Verify configured capture input, playback output, provider BlackHole output,
  capture BlackHole input, and real recording microphone input in one dry-run
  result.
- Keep checks based on existing device discovery; do not change macOS audio
  devices, create Aggregate/Multi-Output devices, switch provider settings, or
  play/record audio.
- Missing audio-device actions should be precise and safe, centered around
  `saymo test-devices`, BlackHole install/setup guidance, and config edits.
- Metadata should include safe device names, kind, required/found state, and
  discovered device properties, without raw audio samples or system secrets.

### Call-Control And LaunchAgent Health
- Verify LaunchAgent install/load/plist currency, daemon running state,
  heartbeat freshness, hotkey availability, hotkey registration status, and log
  paths from the existing call-control status helpers.
- Readiness blockers should distinguish install/start/restart/probe/status
  commands: for example `saymo call-control-agent install/start/restart/status`
  and `saymo call-control probe -p <profile>`.
- Dry-run may read status and heartbeat evidence but must not call install,
  uninstall, start, stop, restart, launchctl mutation, or write heartbeat state.
- Hotkey permission failures should point to Accessibility/GUI-session guidance
  and exact status/probe reruns, not automatic permission repair.

### No Auto-Repair Boundary
- Dry-run diagnostics must not kill apps, change meeting state, switch audio
  devices, switch microphones, toggle mute, start realtime, or restart
  LaunchAgents automatically.
- All provider/audio/control repairs remain copyable commands or manual
  instructions.
- Static tests should guard against provider mutator calls and launchd mutation
  helpers entering the dry-run/readiness path.
- If a check needs live OS state, tests should monkeypatch provider/audio/
  launchd boundaries instead of relying on the current machine.

### Claude's Discretion
- Prefer small optional `rerun_command`/`mode` parameters on existing
  collectors over a separate dry-run provider/audio stack.
- Add tests before production changes and keep implementation narrow to Phase
  50 requirements ENV-01, ENV-02, and ENV-03.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.analysis.provider_audio_readiness.collect_provider_audio_checks`
  already returns provider tab, audio route, provider capability, and
  permission checks.
- `collect_audio_route_checks` already checks configured capture/playback,
  BlackHole 2ch output, BlackHole 16ch input, and real microphone input without
  changing system audio state.
- `saymo.analysis.launch_readiness._collect_call_control_checks` already maps
  `collect_call_control_agent_status` into LaunchReadinessCheck rows for agent,
  daemon, and hotkeys.
- `saymo.analysis.launch_agent.collect_call_control_agent_status` already
  classifies not-installed, installed-not-loaded, stale heartbeat, plist drift,
  running, and hotkey registration state.
- `tests/analysis/test_provider_audio_readiness.py`,
  `tests/analysis/test_launch_agent.py`, `tests/test_call_control_cli.py`, and
  `tests/analysis/test_launch_readiness.py` already cover many pieces.

### Established Patterns
- Provider and audio checks return sanitized `LaunchReadinessCheck` metadata
  with `category` values such as `provider`, `audio-device`, and
  `macos-permission`.
- LaunchAgent mutation functions live behind explicit
  `saymo call-control-agent install/start/stop/restart/uninstall` CLI commands.
- Read-only status commands use `saymo call-control-agent status -p <profile>`
  and `saymo call-control probe -p <profile>`.
- GSD Phase 48/49 dry-run work reused launch-readiness checks and caller mode
  instead of creating a separate schema.

### Integration Points
- `collect_launch_readiness(..., mode="dry-run")` is the top-level dry-run
  integration point.
- `provider_audio_readiness` may need optional dry-run rerun routing and more
  precise remediation strings.
- `_collect_call_control_checks` may need clearer agent/daemon/hotkey actions
  and metadata assertions for dry-run.
- Static guard tests can live near `tests/test_dry_run_cli.py`,
  `tests/analysis/test_provider_audio_readiness.py`, and
  `tests/analysis/test_launch_readiness.py`.

</code_context>

<specifics>
## Specific Ideas

- The user wants "before call one command -> everything ready"; Phase 50 should
  make environmental blockers obvious before joining the meeting.
- Existing `auto-preflight` output already showed `block: provider tab: glip`;
  dry-run should give a better exact action and rerun path.
- The project rule says macOS scheduling should use launchd, not cron; any
  call-control helper guidance should stay launchd/LaunchAgent-based.

</specifics>

<deferred>
## Deferred Ideas

- Phase 51 handles saving/reusing dry-run evidence in rehearsal, scorecards,
  safety-soak, and latest-vs-previous comparisons.
- Automatic provider repair, automatic audio-device switching, automatic
  LaunchAgent restart, and calendar/meeting URL launch remain out of scope.

</deferred>
