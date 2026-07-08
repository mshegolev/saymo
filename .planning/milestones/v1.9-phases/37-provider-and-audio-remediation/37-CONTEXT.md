# Phase 37: Provider and Audio Remediation - Context

**Gathered:** 2026-07-08
**Status:** Ready for planning
**Source:** Smart Discuss auto-accepted for autonomous run

<domain>
## Phase Boundary

Phase 37 extends the Phase 36 `call-ready` gate with provider and audio
readiness. It verifies the configured provider, Chrome meeting tab, provider
capabilities, BlackHole capture/playback routing, real microphone takeover
route, and macOS permission blockers. It must remain non-destructive by
default: no killing Chrome, no leaving meetings, no toggling mute, no changing
system audio routes, and no switching live call microphones unless an explicit
diagnostic command requests that behavior. Daemon/LaunchAgent readiness,
realtime fail-closed enforcement, and scorecard/safety-soak evidence remain
Phases 38-40.

</domain>

<decisions>
## Implementation Decisions

### Readiness Contract

- Reuse the Phase 36 `LaunchReadinessCheck` / `LaunchReadinessReport`
  contracts and keep `saymo call-ready -p <profile> --provider <provider>` as
  the operator entry point.
- Provider/audio checks should become real Phase 37 checks instead of the
  Phase 36 `provider_audio_basic_scope` info placeholder.
- Use the same severity semantics: `block` prevents ready, `warn` is actionable
  but not launch-blocking, and `info` is status-only.
- Human output must keep exact, copyable action/rerun commands; JSON/artifacts
  stay sanitized.

### Provider and Chrome Tab Checks

- Check provider name support through `saymo.providers.factory.get_provider`.
- Check Chrome meeting tab presence via the provider `check_ready()` method,
  but do not activate the tab by default.
- Report provider name, configured provider, provider URL pattern when
  available, `meeting_found`, and window/tab identifiers when present.
- Unknown providers, provider factory errors, AppleScript/Chrome access errors,
  and missing meeting tab are launch blockers with exact remediation.
- Tab activation, focus restore, mute toggling, and JS mic switching are out of
  the default readiness path; they may be represented as capabilities or
  separate explicit diagnostics only.

### Audio Route Checks

- Verify configured capture input (`config.audio.capture_device`) as an input
  device and configured playback output (`config.audio.playback_device`) as an
  output device using `saymo.audio.devices.find_device`.
- Verify provider output target `BlackHole 2ch` as an output device because
  the call app must hear Saymo through that virtual microphone route.
- Verify capture route `BlackHole 16ch` when configured for call capture, but
  do not change the system default input/output.
- Treat missing required BlackHole devices or configured devices as blocking.
  Use `saymo test-devices` / install BlackHole remediation rather than
  automatic system changes.

### Takeover and Real Microphone

- Use the existing `takeover-check` behavior and provider `switch_mic` support
  as the reference for explicit microphone takeover verification.
- In `call-ready`, default to read-only checks: verify
  `config.audio.recording_device` is configured and visible as an input device,
  and report whether the provider exposes `switch_mic` capability.
- Do not switch microphones inside `call-ready` by default. If an explicit
  probe flag is added, it must be opt-in and must switch back to BlackHole
  before reporting ready.
- Provider mic switching support should be actionable per provider: Glip and
  MTS Link have JS-backed implementations; generic Chrome providers currently
  return false and should report a capability limitation.

### macOS Permission Checks

- Reuse hotkey doctor and live-control permission diagnostics where possible,
  especially Accessibility permission guidance for the terminal app running
  Saymo.
- Surface provider automation permission blockers as explicit remediation:
  allow Google Chrome automation / terminal Accessibility permissions, then
  rerun `saymo call-ready`.
- Permission probes must be read-only or reversible. If a probe would create a
  listener or AppleScript event, it should be clearly labeled and avoid
  changing meeting state.

### Non-Destructive Safety

- Phase 37 must include regression tests proving `call-ready` provider/audio
  checks do not call `activate_meeting`, `toggle_mute`, `switch_mic`, leave a
  meeting, kill Chrome, or change system audio routes.
- Any remediation command that mutates state must be explicit and separate
  from the default `call-ready` invocation.
- Existing `auto-preflight` and `takeover-check` commands should remain
  compatible; Phase 37 can extract shared helpers but should not remove these
  commands.

### Claude's Discretion

- Choose module names that match Phase 36 patterns. Preferred direction:
  provider/audio readiness helpers under `saymo.analysis` and thin CLI wiring
  in existing command modules.
- Decide whether to model provider/audio checks in one module or split
  provider and audio route helpers, as long as tests keep the contracts stable.
- Add focused tests before production changes and keep full `uv run pytest`
  green before marking the phase complete.

</decisions>

<specifics>
## Specific Ideas

- Current user-facing blocker from earlier preflight was `provider tab: glip`;
  Phase 37 should turn that into a precise blocker with the provider, Chrome
  tab status, action to open the meeting tab, and a rerun command.
- BlackHole routing should be visible as separate checks for capture input,
  playback output, provider output, and real recording microphone; one generic
  "audio ok" row is not enough.
- Provider capability rows should name limitations such as
  `mic_switch_unsupported`, `tab_activation_supported`, or
  `mute_recovery_supported` without attempting those actions by default.

</specifics>

<canonical_refs>
## Canonical References

### Phase Inputs

- `.planning/REQUIREMENTS.md` - PROV-01 through PROV-05 requirements.
- `.planning/ROADMAP.md` - Phase 37 goal, plan split, dependencies, and
  success criteria.
- `.planning/phases/36-call-ready-preflight-and-cache-gate/36-VERIFICATION.md`
  - Phase 36 readiness contract that Phase 37 extends.
- `.planning/phases/36-call-ready-preflight-and-cache-gate/36-04-SUMMARY.md`
  - Phase 36 collector, artifact, and remediation patterns.

### Existing Provider and Audio Code

- `saymo/analysis/launch_readiness.py` - shared launch-readiness contracts and
  current provider/audio placeholder.
- `saymo/commands/call_ready.py` - current `call-ready` CLI wrapper.
- `saymo/commands/tests.py` - `_collect_auto_preflight`,
  `auto-preflight`, `hotkey-doctor`, `takeover-check`, and related tests.
- `saymo/providers/base.py` - provider protocol and `MeetingStatus`.
- `saymo/providers/_chrome_base.py` - Chrome tab discovery, activation, mute,
  and generic switch-mic behavior.
- `saymo/providers/factory.py` - provider registry and unknown-provider errors.
- `saymo/providers/glip.py` and `saymo/providers/mts_link.py` - JS-backed
  microphone switching examples.
- `saymo/audio/devices.py` - `find_device`, `find_blackhole_devices`, and
  audio-device validation helpers.
- `saymo/analysis/live_control.py` - hotkey doctor and Accessibility
  permission diagnostics.
- `saymo/analysis/remediation.py` - existing remediation categories for
  provider tab, hotkeys, recording microphone, and mic switching.
- `tests/test_takeover_check.py`, `tests/test_trigger_check.py`,
  `tests/test_hotkey_doctor.py`, and `tests/test_call_ready_cli.py` - current
  test patterns for provider/audio diagnostics.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `LaunchReadinessCheck` and grouped remediation from Phase 36 should carry
  Phase 37 checks without a new report format.
- `_collect_auto_preflight` already checks capture input, playback output,
  BlackHole provider output, provider tab, hotkeys, and response cache; Phase
  37 should extract or mirror the provider/audio parts with stricter semantics.
- `takeover-check` already tests explicit mic switching to the real recording
  mic and back to BlackHole, including remediation for missing recording mic
  or missing meeting tab.
- Provider classes expose `check_ready`, `activate_meeting`, `toggle_mute`, and
  `switch_mic`; Phase 37 default checks should call only read-only
  `check_ready`.
- `audio.devices.find_device` is the existing boundary for sounddevice queries.

### Established Patterns

- CLI commands use Click and `ctx.obj["config"]`.
- Tests use `pytest`, `CliRunner`, `MagicMock`, monkeypatching provider factory
  and audio device lookups, and tmp config files.
- Remediation output uses categories like `[retest]`, `[config]`,
  `[macos-permission]`, and exact `rerun:` commands.
- Runtime diagnostics must not leak meeting text, transcripts, note contents,
  audio bytes, or secrets.

### Integration Points

- Replace `provider_audio_basic_scope` in `collect_launch_readiness` with real
  provider/audio checks once helpers exist.
- Add public helpers for provider readiness, audio route readiness, provider
  capability metadata, and optional permission probe status.
- Keep `auto-preflight` and `takeover-check` behavior stable, but allow them
  to reuse new helpers later if that reduces duplication.

</code_context>

<deferred>
## Deferred Ideas

- Automatic provider repair that activates tabs, changes mute state, or
  switches microphones by default is out of scope.
- LaunchAgent/daemon status and hotkey heartbeat belong to Phase 38.
- Realtime startup gating and fail-closed playback enforcement belong to Phase
  39.
- Scorecard/safety-soak evidence and launch health dashboards belong to Phase
  40.
- Native menu bar UI and calendar-based provider launch remain outside v1.9
  Phase 37.

</deferred>

---

*Phase: 37-provider-and-audio-remediation*
*Context gathered: 2026-07-08 via smart discuss auto defaults*
