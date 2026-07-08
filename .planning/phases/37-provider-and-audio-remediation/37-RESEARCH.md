# Phase 37: Provider and Audio Remediation - Research

**Researched:** 2026-07-08
**Domain:** Saymo launch readiness, Chrome provider diagnostics, local audio routing, macOS permission probes
**Confidence:** HIGH for repo-local implementation seams; MEDIUM for microphone-permission probing because the repo has no existing non-recording probe

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)

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
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROV-01 | User can verify the configured provider and Chrome meeting tab are present, identifiable, and actionable before starting realtime mode. | Use `get_provider()` plus provider `check_ready()` only; surface provider name, configured alias, `url_pattern`, `meeting_found`, and `tab_info` as `LaunchReadinessCheck` metadata. |
| PROV-02 | User can verify BlackHole capture/playback routing and the real microphone takeover route before joining or starting the live loop. | Use `saymo.audio.devices.find_device()` with explicit input/output kind checks for configured capture/playback, `BlackHole 2ch`, `BlackHole 16ch` when configured, and `audio.recording_device`. |
| PROV-03 | User can see provider capability details such as tab activation, mic switching support, mute recovery, and unsupported provider limitations without parsing raw errors. | Derive capability metadata from provider class attributes and method overrides; report capabilities without calling mutating provider methods. |
| PROV-04 | User can see macOS permission blockers for hotkeys, microphone capture, Chrome automation, and audio routing with targeted remediation. | Reuse `build_hotkey_doctor_report()` and classify provider/check exceptions as `macos-permission`; add a tightly-scoped, non-recording microphone permission probe only if needed and never use `mic-check` recording paths in `call-ready`. |
| PROV-05 | User can run provider/audio readiness without destructive provider actions such as killing Chrome, leaving a meeting, or changing system routes unless an explicit command requests it. | Regression tests must assert `call-ready` never calls provider mutators, playback functions, `macos_audio.set_input_volume/bump_input_volume`, or config-writing helpers. |
</phase_requirements>

## Summary

Phase 37 should be a narrow extension of the Phase 36 launch-readiness collector. The right implementation is to replace the `provider_audio_basic_scope` info placeholder in `saymo.analysis.launch_readiness` with real `LaunchReadinessCheck` rows from a new analysis helper, while preserving `LaunchReadinessReport`, renderer, JSON artifact shape, and `saymo call-ready` CLI behavior.

The codebase already has most of the primitives: provider lookup and Chrome tab discovery, audio device discovery, hotkey doctor diagnostics, explicit takeover checks, and remediation grouping. The main work is not new infrastructure; it is composing those existing pieces under a non-destructive default policy and adding tests that prove mutating provider/audio functions are not called.

**Primary recommendation:** Add `saymo.analysis.provider_audio_readiness` as the single Phase 37 helper module, have `collect_launch_readiness()` append its checks after the Phase 36 cache/voice checks, and keep mutating operations only in explicit commands such as `takeover-check` and `provider-latency`.

## Standard Stack

### Core

| Library / Module | Version | Purpose | Why Standard |
|------------------|---------|---------|--------------|
| Python | >=3.11 from `pyproject.toml` | Runtime and typing baseline | Project standard. No new runtime needed. |
| `pytest` | 9.0.3 local | Unit and CLI regression tests | Existing test suite uses pytest across `tests/`. |
| `click` | 8.3.2 local | CLI command entry points | `saymo call-ready`, `auto-preflight`, `hotkey-doctor`, and `takeover-check` are Click commands. |
| `rich` | 15.0.0 local | Human CLI rendering | Existing call-ready output uses `console.print(..., soft_wrap=True)`. |
| `sounddevice` | 0.5.5 local | Audio device discovery and optional probes | `saymo.audio.devices` is the repo-local boundary for device queries. |
| `pynput` | 1.8.1 local | Global hotkey registration probe | Existing hotkey doctor uses `keyboard.GlobalHotKeys`. |
| `pyyaml` | 6.0.3 local | Config tests and config generation | Existing config/test helpers already use YAML. |

### Supporting

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `saymo.analysis.launch_readiness` | Shared report/check contract, renderer, artifact writer | Keep the Phase 37 output contract and readiness semantics. |
| `saymo.providers.factory` | Provider alias registry and unknown-provider error | Always resolve providers here; do not instantiate provider classes directly. |
| `saymo.providers._chrome_base` | Chrome tab discovery, activation, mute, generic mic-switch fallback | Use only `check_ready()` in default readiness. Capability metadata can inspect methods/attributes without calling mutators. |
| `saymo.audio.devices` | `find_device`, `find_blackhole_devices`, `validate_devices` | All sounddevice queries should stay behind this module. |
| `saymo.analysis.live_control` | Hotkey doctor report and permission guidance | Reuse for hotkey/Accessibility readiness. |
| `saymo.analysis.remediation` | Remediation hint model and launch grouping | Extend `_launch_category_for_check()` / launch hints rather than adding a second renderer. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One `provider_audio_readiness.py` helper | Split `provider_readiness.py`, `audio_readiness.py`, `permission_readiness.py` | Splitting is cleaner long-term, but one helper is lower churn and fits the Phase 37 surface. Split later only if tests become hard to read. |
| `LaunchReadinessCheck` rows | New provider/audio report dataclass | New report would duplicate Phase 36 rendering, artifact, and remediation code. |
| `auto-preflight` `PreflightCheck` | Reuse `_collect_auto_preflight()` directly | `_collect_auto_preflight()` mixes prepared audio/cache/live tuning and has weaker metadata; Phase 37 needs stable JSON/artifact fields. |
| Actual mic switching probe in `call-ready` | Existing `takeover-check` | `takeover-check` intentionally mutates provider mic state; default `call-ready` must not. |

**Installation:**

```bash
uv sync
```

No new dependency is required for Phase 37.

**Version verification:**

```bash
uv run python - <<'PY'
import importlib.metadata as m
for name in ["pytest", "click", "rich", "sounddevice", "pynput", "pyyaml"]:
    print(name, m.version(name))
PY
```

Verified locally on 2026-07-08: `pytest 9.0.3`, `click 8.3.2`, `rich 15.0.0`, `sounddevice 0.5.5`, `pynput 1.8.1`, `pyyaml 6.0.3`.

## Architecture Patterns

### Recommended Project Structure

```text
saymo/
  analysis/
    launch_readiness.py          # append Phase 37 checks, keep report/rendering
    provider_audio_readiness.py  # new: provider, audio route, capability, permission checks
    remediation.py               # extend launch check categories if needed
tests/
  analysis/
    test_provider_audio_readiness.py
    test_launch_readiness.py
  test_call_ready_cli.py
```

### Pattern 1: Append Domain Checks Through LaunchReadinessCheck

**What:** `provider_audio_readiness.collect_provider_audio_checks(config, profile, provider_name)` should return a tuple of `LaunchReadinessCheck` rows. `launch_readiness.collect_launch_readiness()` appends those rows after cloned-voice metadata, replacing `_provider_audio_basic_scope_check()`.

**When to use:** For all Phase 37 checks that must appear in human output, JSON, artifacts, and grouped remediation.

**Example:**

```python
# Source: repo pattern from saymo.analysis.launch_readiness
checks.append(
    collect_voice_metadata_check(
        config,
        profile=profile,
        provider_name=provider_name,
    )
)
checks.extend(
    collect_provider_audio_checks(
        config,
        profile=profile,
        provider_name=provider_name,
    )
)
```

### Pattern 2: Default Provider Checks Are Read-Only

**What:** Provider readiness may call `get_provider()` and `provider.check_ready()` only. It must not call `activate_meeting()`, `toggle_mute()`, `switch_mic()`, `get_previous_app()`, or `activate_app()`.

**When to use:** Every `call-ready` provider check and every CLI smoke path that invokes launch readiness.

**Example:**

```python
# Source: repo provider protocol + Phase 37 safety constraint
try:
    provider = get_provider(provider_name)
    status = provider.check_ready()
except Exception as exc:
    return _blocked_provider_check(provider_name, str(exc))

return LaunchReadinessCheck(
    key="provider_meeting_tab",
    label="provider meeting tab",
    severity="block",
    ok=bool(status.meeting_found),
    detail="meeting_found" if status.meeting_found else "meeting_tab_not_found",
    action=f"Open the {provider.name} meeting in Chrome",
    rerun=f"saymo call-ready -p {profile} --provider {provider_name}",
    metadata={
        "provider_name": provider.name,
        "configured_provider": provider_name,
        "url_pattern": getattr(provider, "url_pattern", ""),
        "meeting_found": bool(status.meeting_found),
        "tab_info": list(status.tab_info) if status.tab_info else None,
    },
)
```

### Pattern 3: Audio Route Checks Use Explicit Device Kind

**What:** Use `find_device(name, kind="input")` for capture and real recording mic; use `find_device(name, kind="output")` for playback and `BlackHole 2ch`.

**When to use:** All PROV-02 audio route checks.

**Example:**

```python
# Source: repo boundary from saymo.audio.devices
capture = find_device(config.audio.capture_device, kind="input")
playback = find_device(config.audio.playback_device, kind="output")
provider_output = find_device("BlackHole 2ch", kind="output")
real_mic = find_device(config.audio.recording_device, kind="input")
```

### Pattern 4: Capabilities Are Metadata, Not Actions

**What:** Report capability rows such as `tab_activation_supported`, `mute_recovery_supported`, and `mic_switch_supported` from provider class structure and known implementations. Do not execute those capabilities in `call-ready`.

**When to use:** PROV-03 and unsupported-provider limitations.

**Example:**

```python
# Source: repo provider classes
mic_switch_supported = provider.__class__.__name__ in {
    "GlipProvider",
    "MTSLinkProvider",
}
metadata = {
    "tab_activation_supported": hasattr(provider, "activate_meeting"),
    "mute_recovery_supported": hasattr(provider, "toggle_mute"),
    "mic_switch_supported": mic_switch_supported,
    "mic_switch_status": "supported" if mic_switch_supported else "unsupported",
}
```

### Anti-Patterns to Avoid

- **Calling provider mutators from `call-ready`:** `activate_meeting`, `toggle_mute`, `switch_mic`, focus restore, and JS mic switching change meeting state or UI focus. Keep them in explicit diagnostics.
- **Using `auto-preflight` wholesale:** It produces `PreflightCheck`, lacks Phase 37 metadata, and includes unrelated cache/live-tuning rows.
- **Treating device name existence as route correction:** `find_device()` proves visibility only. It must not change macOS defaults or provider-selected mics.
- **Using `mic-check` internals from `call-ready`:** `mic-check` records audio, plays back audio, can write `~/.saymo/config.yaml`, and in `--auto` can change system input volume.
- **Adding raw AppleScript stderr or device dumps to artifacts:** Keep metadata bounded and sanitized.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Provider alias resolution | New registry or string matching | `saymo.providers.factory.get_provider` | Existing registry covers aliases and emits available provider list. |
| Chrome meeting discovery | Custom AppleScript in analysis helper | provider `check_ready()` | Provider classes already own URL patterns and tab lookup. |
| Audio device search | Direct `sounddevice.query_devices()` in launch checks | `saymo.audio.devices.find_device` | Centralizes untyped `sounddevice` handling and input/output channel filtering. |
| Hotkey Accessibility check | New pynput listener wrapper | `build_hotkey_doctor_report()` | Existing report covers bindings, process status, registration probe, and remediation. |
| Takeover mic switching | Default call-ready switch/revert flow | `takeover-check` for explicit probe | Existing command already switches to real mic and back to `BlackHole 2ch`. |
| Remediation output | Separate provider/audio renderer | `LaunchReadinessCheck` action/rerun + `hints_from_launch_readiness()` | Keeps Phase 36 block/warn/info grouping and artifact shape stable. |
| System audio fixes | Route changes, input-volume bumps, config writes | `saymo test-devices`, `saymo mic-check`, explicit user actions | Phase 37 default must remain non-destructive. |

**Key insight:** The complex part is safety boundaries, not discovery. The repo already knows how to find providers, devices, and hotkey issues; Phase 37 must package those checks without accidentally invoking the mutating paths that were built for explicit diagnostics.

## Common Pitfalls

### Pitfall 1: `check_ready()` Can Hide Chrome Automation Failures

**What goes wrong:** `ChromeCallProvider.check_ready()` calls `_run_applescript()`, whose current helper logs AppleScript errors and returns stdout. Empty stdout can look like "tab not found" instead of an Automation permission blocker.

**Why it happens:** The low-level helper does not currently return stderr/status to callers.

**How to avoid:** In Phase 37, either add a checked AppleScript helper for tab discovery or classify exceptions from provider checks distinctly. If the helper cannot reliably distinguish permission denial, use a conservative blocker detail such as `meeting_tab_not_found_or_chrome_automation_blocked` with remediation for both opening the tab and allowing Chrome automation.

**Warning signs:** Tests can only cover provider exceptions, not silent AppleScript failures; human output says only "tab not found" when Chrome permissions are actually blocked.

### Pitfall 2: Generic Chrome Providers Return `switch_mic=False`

**What goes wrong:** A generic provider can be usable for tab/mute, but unable to switch the call mic automatically.

**Why it happens:** `ChromeCallProvider.switch_mic()` logs a warning and returns `False`; only Glip and MTS Link override it with JS-backed implementations.

**How to avoid:** Report `mic_switch_supported=false` as a provider capability limitation. Do not call `switch_mic()` in `call-ready`.

**Warning signs:** Capability row says "unsupported" but readiness still implies takeover can be fully automated.

### Pitfall 3: Input and Output Device Kinds Are Easy to Invert

**What goes wrong:** `BlackHole 2ch` must be checked as an output device for Saymo playback into the provider, while `BlackHole 16ch` and the real mic must be checked as inputs.

**Why it happens:** BlackHole names sound like "microphones" from the call-app perspective, but Saymo sends audio to BlackHole through an output route.

**How to avoid:** Every check name should encode kind: `capture_input`, `playback_output`, `provider_output_blackhole`, `recording_microphone_input`.

**Warning signs:** Tests pass with `find_device(name, kind=None)` or call `find_device("BlackHole 2ch", kind="input")`.

### Pitfall 4: Permission Probes Can Become Hidden Side Effects

**What goes wrong:** Hotkey, Chrome automation, or microphone probes can create listeners, AppleScript events, or audio streams without the operator understanding what happened.

**Why it happens:** Permission checks are often performed by attempting the action.

**How to avoid:** Keep probes labeled in check details. Hotkey probe should start/stop only a dummy listener. Chrome probe should only read tab URLs. If microphone permission needs to be proved, use a minimal open/close input stream helper that stores no audio, records no file, runs no STT, and has focused tests.

**Warning signs:** `call-ready` imports `mic_check`, calls `sd.rec`, writes config, plays audio, or changes macOS input volume.

### Pitfall 5: Sanitized Artifacts Can Drift from Human Output

**What goes wrong:** Human output gets new provider/audio detail, but JSON artifacts omit or leak fields.

**Why it happens:** Adding ad hoc print logic bypasses `LaunchReadinessCheck.to_dict()`.

**How to avoid:** Put every field in `metadata` and rely on `report.to_dict()`. Keep long remediation text in `action` and exact reruns in `rerun`.

**Warning signs:** CLI output has provider tab identifiers but `--json` or `--output` does not.

## Code Examples

Verified patterns from repo-local sources:

### Launch Check Shape

```python
# Source: saymo.analysis.launch_readiness
LaunchReadinessCheck(
    key="provider_meeting_tab",
    label="provider meeting tab",
    severity="block",
    ok=False,
    detail="meeting_tab_not_found",
    action="Open the glip meeting in Chrome",
    rerun="saymo call-ready -p standup --provider glip",
    metadata={"provider_name": "glip", "meeting_found": False},
)
```

### Non-Destructive Provider Test Pattern

```python
# Source: existing tests use MagicMock/CliRunner/monkeypatch
provider = MagicMock()
provider.name = "glip"
provider.check_ready.return_value = MeetingStatus(
    app_running=True,
    meeting_found=True,
    tab_info=(1, 2),
)

report = collect_launch_readiness(config, profile="standup", provider_name="glip")

provider.check_ready.assert_called_once()
provider.activate_meeting.assert_not_called()
provider.toggle_mute.assert_not_called()
provider.switch_mic.assert_not_called()
```

### Audio Device Lookup Test Pattern

```python
# Source: existing auto-preflight tests monkeypatch saymo.audio.devices.find_device
calls = []

def fake_find_device(name, kind="input"):
    calls.append((name, kind))
    return object() if name else None

monkeypatch.setattr("saymo.audio.devices.find_device", fake_find_device)
```

### Hotkey Doctor Reuse

```python
# Source: saymo.analysis.live_control
report = build_hotkey_doctor_report(config, profile, probe=True)
status = report.registration_status  # ok, skipped, no_bindings, missing_dependency, blocked
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `provider_audio_basic_scope` info placeholder | Real provider/audio checks in Phase 37 | Phase 37 | `call-ready` becomes a true provider/audio launch gate. |
| `auto-preflight` `PreflightCheck` for operator diagnostics | `LaunchReadinessCheck` with sanitized JSON artifacts | Phase 36 | Phase 37 should use the launch contract, not auto-preflight output. |
| Explicit `takeover-check` switches mic to real device and back | Default `call-ready` only reports real mic visibility and switch capability | Phase 37 | Keeps automatic remediation out of the readiness path. |
| `provider-latency` activates tab, toggles mute, plays audio, restores focus | Phase 37 readiness reports those capabilities without using them | Existing command remains explicit | Avoids meeting disruption during pre-call checks. |
| `mic-check --auto` can write config and raise input volume | Phase 37 default should not use calibration internals | Existing command remains explicit | Prevents hidden system audio changes. |

**Deprecated/outdated:**

- `provider_audio_basic_scope`: intentional Phase 36 placeholder; replace in Phase 37.
- Any plan to repair provider state inside `call-ready`: out of scope by user decision.
- Any plan to move daemon/heartbeat status into Phase 37: defer to Phase 38.

## Open Questions

1. **How strongly should Phase 37 prove microphone permission?**
   - What we know: device visibility is easy through `find_device()`, and `mic-check` can record audio, but there is no current non-recording permission probe.
   - What's unclear: whether default `call-ready` should open/close an input stream to force macOS microphone permission validation.
   - Recommendation: start with device visibility plus targeted remediation; if PROV-04 is judged incomplete, add a small no-storage input-stream probe under `provider_audio_readiness` and tests proving it does not call `sd.rec`, save audio, or transcribe.

2. **Should silent AppleScript failures be made explicit?**
   - What we know: `_run_applescript()` logs stderr and returns stdout; `check_ready()` only sees the returned text.
   - What's unclear: whether macOS Automation denial returns enough stdout/stderr in the current environment to distinguish from no matching tab.
   - Recommendation: make provider-readiness tests cover raised exceptions now; consider adding a checked AppleScript result helper if manual verification shows permission denial is ambiguous.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none; tests are discovered by pytest defaults and `pyproject.toml` declares the dev dependency |
| Quick run command | `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| PROV-01 | Provider aliases resolve; unknown provider/factory errors block; Chrome tab status includes provider name, configured provider, URL pattern, `meeting_found`, and tab identifiers. | unit + CLI | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_provider_tab_readiness_reports_found_missing_and_errors tests/test_call_ready_cli.py::test_call_ready_includes_provider_tab_readiness -q` | No - Wave 0 |
| PROV-02 | Capture input, playback output, `BlackHole 2ch` provider output, `BlackHole 16ch` capture route, and real recording mic are validated with correct input/output kinds. | unit | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_audio_route_checks_validate_expected_devices_and_kinds -q` | No - Wave 0 |
| PROV-03 | Provider capabilities report tab activation, mute recovery, mic switching support, and unsupported limitations without calling mutating methods. | unit | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_provider_capabilities_are_reported_without_actions -q` | No - Wave 0 |
| PROV-04 | Hotkey, Chrome automation, microphone capture, and audio-routing permission failures map to targeted remediation categories and exact rerun commands. | unit + remediation | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_permission_blockers_are_actionable tests/analysis/test_remediation.py::test_launch_provider_audio_hints_classify_permissions -q` | No - Wave 0 |
| PROV-05 | Default `call-ready` does not activate tabs, toggle mute, switch mics, leave meetings, kill Chrome, change system routes, play audio, record audio, or write audio config. | unit + CLI regression | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_collect_provider_audio_checks_is_non_destructive tests/test_call_ready_cli.py::test_call_ready_provider_audio_checks_are_non_destructive -q` | No - Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
- **Per wave merge:** `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/test_hotkey_doctor.py tests/analysis/test_remediation.py -q`
- **Phase gate:** `uv run pytest` must be green before `/gsd:verify-work`.

### Wave 0 Gaps

- [ ] `tests/analysis/test_provider_audio_readiness.py` - covers PROV-01 through PROV-05 helper behavior.
- [ ] `tests/test_call_ready_cli.py` - add call-ready rows/artifact/non-destructive assertions for PROV-01 and PROV-05.
- [ ] `tests/analysis/test_launch_readiness.py` - update Phase 36 placeholder order test to expect Phase 37 real checks.
- [ ] `tests/analysis/test_remediation.py` - add launch provider/audio category coverage for `audio-device`, `provider`, and `macos-permission`.

## Sources

### Primary (HIGH confidence)

- `.planning/phases/37-provider-and-audio-remediation/37-CONTEXT.md` - locked scope, safety boundaries, implementation decisions.
- `.planning/REQUIREMENTS.md` - PROV-01 through PROV-05 wording and phase mapping.
- `.planning/ROADMAP.md` - Phase 37 goal, plans, dependencies, success criteria.
- `.planning/STATE.md` - Phase 36 completion state and open provider/audio concerns.
- `.planning/phases/36-call-ready-preflight-and-cache-gate/36-VERIFICATION.md` - verified Phase 36 contract and deferred Phase 37 scope.
- `.planning/phases/36-call-ready-preflight-and-cache-gate/36-04-SUMMARY.md` - collector order, remediation, artifact patterns.
- `CLAUDE.md` and `AGENTS.md` - Saymo architecture, local-by-default rules, commands, testing conventions.
- `.claude/skills/test-tts/SKILL.md` - local project skill index; not directly used for Phase 37 planning.
- `saymo/analysis/launch_readiness.py` - LaunchReadiness contracts, renderer, artifact writer, Phase 37 placeholder.
- `saymo/commands/call_ready.py` - current CLI wrapper and JSON/artifact behavior.
- `saymo/commands/tests.py` - `auto-preflight`, `hotkey-doctor`, `provider-latency`, `takeover-check`, `mic-check` patterns and mutation boundaries.
- `saymo/providers/base.py`, `saymo/providers/_chrome_base.py`, `saymo/providers/factory.py`, `saymo/providers/glip.py`, `saymo/providers/mts_link.py` - provider protocol, Chrome tab lookup, provider registry, mic-switch support.
- `saymo/audio/devices.py`, `saymo/audio/macos_audio.py`, `saymo/audio/playback.py`, `saymo/audio/capture.py`, `saymo/audio/multi_play.py` - audio discovery and mutating playback/system audio functions to avoid in default readiness.
- `saymo/analysis/live_control.py`, `saymo/analysis/remediation.py` - hotkey diagnostics and remediation grouping.
- `tests/analysis/test_launch_readiness.py`, `tests/test_call_ready_cli.py`, `tests/test_takeover_check.py`, `tests/test_hotkey_doctor.py`, `tests/test_provider_latency.py`, `tests/test_trigger_check.py`, `tests/analysis/test_remediation.py` - current test patterns.

### Secondary (MEDIUM confidence)

- Local installed package metadata from `uv run python` - current dependency versions in this checkout.
- `/Users/m.v.shchegolev/.codex/memories/MEMORY.md` - prior Saymo note that `auto-preflight -p personal` is used as a quick voice-profile readiness check; relevant only as background, not as current implementation truth.

### Tertiary (LOW confidence)

- None. No external web search was used per user instruction.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - verified from `pyproject.toml` and local installed package metadata.
- Architecture: HIGH - based on current Phase 36 contracts and existing provider/audio code.
- Pitfalls: HIGH for non-destructive provider/audio boundaries; MEDIUM for microphone permission detection because the repo lacks a dedicated non-recording probe.
- Validation architecture: HIGH - based on existing pytest layout and current targeted tests.

**Research date:** 2026-07-08
**Valid until:** 2026-08-07, or earlier if provider automation helpers or audio command boundaries change.
