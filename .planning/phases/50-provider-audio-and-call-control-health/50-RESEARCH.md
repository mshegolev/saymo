# Phase 50: Provider, Audio, And Call-Control Health - Research

**Researched:** 2026-07-10
**Domain:** macOS local readiness diagnostics, Chrome call-provider checks, BlackHole audio routing, LaunchAgent call-control health
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

- Phase 51 handles saving/reusing dry-run evidence in rehearsal, scorecards,
  safety-soak, and latest-vs-previous comparisons.
- Automatic provider repair, automatic audio-device switching, automatic
  LaunchAgent restart, and calendar/meeting URL launch remain out of scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENV-01 | User can verify provider tab readiness, Chrome/provider state, BlackHole capture/playback devices, and audio routing prerequisites in one dry-run result. | Reuse `collect_provider_audio_checks` and add dry-run-aware action/rerun plumbing plus metadata assertions. |
| ENV-02 | User can verify call-control daemon and LaunchAgent health, including heartbeat freshness, hotkey availability, stale plist status, and exact restart/probe commands. | Reuse `collect_call_control_agent_status` through `_collect_call_control_checks`; tighten command/action mapping and metadata tests. |
| ENV-03 | User can keep provider repair explicit: dry-run diagnostics may suggest safe commands but must not kill apps, change meeting state, or switch devices automatically. | Add static and monkeypatch guards around dry-run, provider/audio collectors, and launchd status boundaries. |
</phase_requirements>

## Summary

Phase 50 should not introduce a new health-check subsystem. The project already has the right primitives: `collect_launch_readiness(..., mode="dry-run")` is the orchestration point, `LaunchReadinessCheck` is the shared result contract, `provider_audio_readiness` already collects provider tab and audio-route checks, and `launch_agent.collect_call_control_agent_status` already classifies LaunchAgent, heartbeat, plist drift, crash, and hotkey states.

The main planning need is to make these existing collectors dry-run-aware and operator-facing. Today provider/audio checks still emit `saymo call-ready ...` reruns and call-ready phrasing from a shared `_rerun()` helper. Phase 50 should add narrow optional `rerun_command`/`mode` parameters to provider/audio collectors, route dry-run through those parameters from `launch_readiness`, and preserve `call-ready` defaults for older tests.

Call-control health should remain read-only in dry-run. `call-control-agent status` reads plist, `plutil`, `launchctl print`, and heartbeat evidence; `call-control probe` writes a benign status command and waits for audit proof, so dry-run should suggest the probe command but not invoke it.

**Primary recommendation:** Add RED tests first for dry-run-specific provider/audio/control output, then implement caller-aware rerun/action strings by threading `rerun_command` through existing collectors; do not add dependencies or live OS repair behavior.

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Python | `>=3.11` project requirement; local `3.12` used by uv | Core implementation | Existing package/runtime standard. |
| Click | Installed `8.3.2`; PyPI current `8.4.2` published 2026-06-24 | CLI commands and `CliRunner` tests | Existing Saymo CLI stack; no Phase 50 need to upgrade. |
| pytest | Installed `9.0.3`; PyPI current `9.1.1` published 2026-06-19 | Unit/CLI/static tests | Existing test framework; monkeypatch is the right boundary tool. |
| sounddevice | Installed/PyPI current `0.5.5` published 2026-01-23 | Device discovery and input/output setting probes | Existing audio-device boundary; docs support `query_devices`, `check_input_settings`, `check_output_settings`. |
| plistlib | Python stdlib | Deterministic LaunchAgent plist rendering/parsing | Existing code uses `plistlib.dumps(..., fmt=FMT_XML, sort_keys=True)`; avoids manual XML. |
| launchctl / plutil | macOS system tools | Read LaunchAgent service and plist validity | Existing argv builders isolate `print`, `bootstrap`, `bootout`, `kickstart`, and `plutil -lint`. |
| pynput | Installed `1.8.1`; PyPI current `1.8.2` published 2026-05-12 | Global hotkey registration in daemon | Existing daemon dependency; dry-run reads heartbeat status only. |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| PyYAML | Installed/PyPI current `6.0.3` published 2025-09-25 | Config loading | Existing config parser; do not bypass config dataclasses. |
| Rich | Existing project dependency | Console output | Keep using existing `console.print` rendering path. |
| AppleScript via provider base | Existing local code | Chrome tab detection through `check_ready()` | Use only read-only tab detection; never call mutators in dry-run. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing `LaunchReadinessCheck` | New dry-run schema | Reject: Phase 48 already established the shared result/artifact contract. |
| `sounddevice.query/check_*` | Real audio recording/playback | Reject: violates ENV-03 and can disturb devices/calls. |
| `launchctl print` status boundary | `launchctl kickstart/start/restart` in dry-run | Reject: status is read-only; lifecycle commands remain explicit operator actions. |
| LaunchAgent | cron | Reject: project instructions require launchd for macOS scheduled/background tasks. |
| Existing provider `check_ready()` | Activating/focusing Chrome tabs or toggling mute | Reject: changes meeting state and violates Phase 50 constraints. |

**Installation:**
```bash
uv sync
```

No new package install is recommended for Phase 50.

**Version verification:**
```bash
uv run python -c "import importlib.metadata as m; pkgs=['click','sounddevice','pytest','pynput','PyYAML']; print('\n'.join(f'{p}=={m.version(p)}' for p in pkgs))"
curl -fsSL https://pypi.org/pypi/<package>/json
```

Registry check succeeded with `curl` after local Python SSL certificate verification failed for `urllib.request`. Results: Click `8.4.2`, sounddevice `0.5.5`, pytest `9.1.1`, pynput `1.8.2`, PyYAML `6.0.3`.

## Architecture Patterns

### Recommended Project Structure

```text
saymo/
├── analysis/
│   ├── launch_readiness.py          # top-level dry-run/call-ready orchestration
│   ├── provider_audio_readiness.py  # provider, Chrome, audio, permission checks
│   ├── launch_agent.py              # LaunchAgent spec/status/read-only classification
│   └── control_daemon.py            # heartbeat/probe evidence, not dry-run execution
├── commands/
│   ├── dry_run.py                   # CLI wrapper, no direct provider/audio/launchd mutators
│   └── call_control.py              # explicit status/probe/lifecycle commands
└── tests/
    ├── analysis/
    │   ├── test_provider_audio_readiness.py
    │   ├── test_launch_readiness.py
    │   ├── test_launch_agent.py
    │   └── test_control_daemon.py
    ├── test_call_control_cli.py
    └── test_dry_run_cli.py
```

### Pattern 1: Caller-Aware Existing Collectors

**What:** Thread a `rerun_command` or `mode` parameter into existing collectors and keep `call-ready` as the default.
**When to use:** Any existing check currently emits `saymo call-ready ...` but dry-run needs `saymo dry-run ...`.

**Example:**
```python
# Source: existing launch_readiness dry-run pattern
rerun_command = _launch_rerun_command(mode, profile, provider_name)
checks.extend(
    collect_provider_audio_checks(
        config,
        profile=profile,
        provider_name=provider_name,
        rerun_command=rerun_command,
        mode=mode,
    )
)
```

### Pattern 2: Read-Only Boundary With Explicit Mutators Elsewhere

**What:** Status collectors may read files and run status commands; lifecycle helpers stay behind explicit CLI commands.
**When to use:** LaunchAgent and call-control health.

**Example:**
```python
# Source: existing launch_agent status boundary
plutil_result = command_runner(plutil_lint_argv(spec), check=False)
launchctl_result = command_runner(print_argv(spec), check=False)
heartbeat = load_daemon_heartbeat(spec.profile, base_dir=base_dir)
```

### Pattern 3: Structured Checks With Sanitized Metadata

**What:** All health facts are `LaunchReadinessCheck` rows with stable `key`, `severity`, `detail`, `action`, `rerun`, and metadata categories.
**When to use:** Every Phase 50 diagnostic.

**Example:**
```python
# Source: existing audio metadata shape
metadata = {
    "category": "audio-device",
    "device_name": device_name,
    "kind": kind,
    "required": True,
    "found": device is not None,
}
```

### Anti-Patterns to Avoid

- **Separate dry-run provider/audio stack:** It will drift from `call-ready`; add optional caller context to existing collectors instead.
- **Implicit repair from diagnostics:** Do not call `install_launch_agent`, `start_launch_agent`, `restart_launch_agent`, provider `activate_meeting`, provider `toggle_mute`, `switch_mic`, playback, recording, or config writers.
- **Parsing launchctl free text as the only truth:** Use existing classification plus heartbeat/plist evidence; keep bounded excerpts only as metadata.
- **Testing against the developer machine:** Monkeypatch provider factory, `audio_devices.find_device`, sounddevice check functions, `Path.home`, `shutil.which`, `os.getuid`, and `launch_agent.run_command`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dry-run result model | New JSON/Markdown schema | `LaunchReadinessReport` / `LaunchReadinessCheck` | Phase 48 already verified this contract and renderer. |
| Plist generation/drift | Manual XML/string comparison | `plistlib.dumps(..., sort_keys=True)` and SHA-256 | Avoids malformed plist and unstable key ordering. |
| LaunchAgent command lines | Shell strings | Existing `bootstrap_argv`, `bootout_argv`, `kickstart_argv`, `print_argv`, `plutil_lint_argv` | Avoids quoting bugs and keeps tests simple. |
| Audio-device proof | Recording/playback probes | `sounddevice.query_devices`, `check_input_settings`, `check_output_settings` through existing helpers | Real streams disturb calls and require hardware. |
| Provider readiness | Chrome focus/mute/mic control | Provider `check_ready()` only | Mutators change live meeting state. |
| Hotkey proof in dry-run | Starting listener/probe command | Existing heartbeat status plus suggested `saymo call-control probe -p <profile>` | Probe writes command/audit evidence; keep it explicit. |

**Key insight:** Phase 50 is a diagnostics presentation and safety-boundary phase, not a repair automation phase. Custom repair logic is riskier than precise operator commands because the checked resources are live Chrome tabs, macOS audio devices, and LaunchAgent state.

## Common Pitfalls

### Pitfall 1: Dry-Run Output Still Says Call-Ready

**What goes wrong:** Provider/audio actions and reruns point at `saymo call-ready ...` because `provider_audio_readiness._rerun()` is hardcoded.
**Why it happens:** Phase 49 added dry-run rerun plumbing for source/cache/voice, but provider/audio collectors predate it.
**How to avoid:** Add optional `rerun_command` to `collect_provider_audio_checks`, `collect_audio_route_checks`, `collect_provider_tab_check`, `collect_provider_capability_checks`, and `collect_permission_checks`.
**Warning signs:** Tests find `saymo call-ready` in dry-run provider/audio/check permission output.

### Pitfall 2: Probe Is Treated As Read-Only

**What goes wrong:** Dry-run invokes `run_handbrake_reachability_probe()` to prove reachability.
**Why it happens:** The probe is safe for operators, but it writes a status command and waits for audit evidence.
**How to avoid:** Dry-run should read `collect_call_control_agent_status()` only and recommend `saymo call-control probe -p <profile>` as a rerun/action.
**Warning signs:** Dry-run tests create `commands.jsonl` or `audit.jsonl`.

### Pitfall 3: LaunchAgent Status Accidentally Mutates launchd

**What goes wrong:** Status path calls `bootstrap`, `bootout`, or `kickstart`.
**Why it happens:** Lifecycle helpers live in the same module as status helpers.
**How to avoid:** Keep dry-run routed only through `collect_call_control_agent_status`; add static guards and monkeypatch mutators to fail tests.
**Warning signs:** Recorded launchctl argv contains `bootstrap`, `bootout`, or `kickstart`.

### Pitfall 4: Provider Capability Checks Call Provider Actions

**What goes wrong:** Capability detection invokes `activate_meeting`, `toggle_mute`, or `switch_mic`.
**Why it happens:** Capabilities are methods on the provider object, so it is easy to probe by calling.
**How to avoid:** Use `callable(getattr(...))` and method identity comparison only, as existing code does.
**Warning signs:** MagicMock provider mutator assertions fail.

### Pitfall 5: Permission Checks Become Hardware Tests

**What goes wrong:** Audio permissions are tested by recording or playback.
**Why it happens:** Missing permission and missing device can look similar.
**How to avoid:** Keep the existing `sd.check_input_settings` and `sd.check_output_settings` pattern; do not call `sd.rec` or playback helpers.
**Warning signs:** Tests need real microphone, speakers, or BlackHole installed.

### Pitfall 6: Metadata Leaks Raw Evidence

**What goes wrong:** Provider payloads, raw AppleScript output, audio bytes, transcript windows, or secret-like strings land in JSON.
**Why it happens:** Launch readiness artifacts are convenient debugging containers.
**How to avoid:** Keep metadata to booleans, labels, paths, device properties, bounded excerpts, hashes, and sanitized error types.
**Warning signs:** Private sentinel tests fail or output includes raw meeting/provider/audio content.

## Code Examples

Verified patterns from current code and official docs:

### Dry-Run Command Delegates To Shared Readiness

```python
# Source: saymo/commands/dry_run.py
report = collect_launch_readiness(
    config,
    profile=profile,
    provider_name=resolved_provider,
    prepare=prepare_source,
    mode="dry-run",
)
```

### Device Readiness Without Audio Streams

```python
# Source: saymo/analysis/provider_audio_readiness.py and sounddevice docs
device = audio_devices.find_device("BlackHole 16ch", kind="input")
if device is not None:
    sd.check_input_settings(device=device.index, samplerate=device.default_samplerate)
```

### LaunchAgent Read-Only Status

```python
# Source: saymo/analysis/launch_agent.py
plutil_result = command_runner(plutil_lint_argv(spec), check=False)
launchctl_result = command_runner(print_argv(spec), check=False)
heartbeat = load_daemon_heartbeat(spec.profile, base_dir=base_dir)
```

### Static Guard For Dry-Run Safety

```python
# Source: tests/test_dry_run_cli.py
FORBIDDEN_DRY_RUN_REFERENCES = (
    "_auto",
    "_play_cached_audio",
    "activate_meeting",
    "toggle_mute",
    "switch_mic",
    "saymo.audio",
    "saymo.providers",
    "saymo.tts",
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate ad hoc CLI checks | Shared `LaunchReadinessReport` and renderer | Phase 48, 2026-07-10 | Plans should extend shared checks, not create new schemas. |
| Call-ready-only reruns | Caller-aware dry-run reruns for source/cache/voice | Phase 49, 2026-07-10 | Apply the same pattern to provider/audio/control. |
| LaunchAgent lifecycle as smoke check | Read-only status plus explicit status/probe/start/restart commands | Existing Phase 40/50 context | Dry-run can diagnose but must not mutate launchd. |
| Real audio smoke as readiness proof | Device discovery/settings checks plus explicit `saymo test-devices` guidance | Existing audio readiness tests | Unit tests can run without BlackHole/hardware. |

**Deprecated/outdated:**
- Cron for macOS background tasks: project instructions require launchd/LaunchAgent.
- Automatic provider tab activation for readiness: out of scope for Phase 50 because it changes meeting state.
- Real audio playback/recording inside dry-run: out of scope and explicitly unsafe.

## Open Questions

1. **Should dry-run provider blockers suggest `saymo provider-latency` only when a meeting tab is found?**
   - What we know: Context asks for exact provider diagnostic commands, including `saymo provider-latency`.
   - What's unclear: `provider-latency` appears to require an active call path and may not be useful when Chrome/tab is absent.
   - Recommendation: For missing tab, action should be "Open the provider meeting in Chrome"; for provider check errors or capability warnings, include `saymo provider-latency -p <profile>` only if tests confirm it is safe/operator-run guidance.

2. **Should missing LaunchAgent install be a blocker for every dry-run?**
   - What we know: ENV-02 says user can verify daemon and LaunchAgent health; existing `_collect_call_control_checks` treats agent/daemon/hotkeys as blocking.
   - What's unclear: Some profiles may not rely on call-control handbrake yet.
   - Recommendation: Keep current blocking behavior for Phase 50; changing severity is product behavior and should be a separate decision.

3. **Should provider/audio permission checks use dry-run wording for macOS Accessibility app names?**
   - What we know: Existing action text says terminal app and call-ready.
   - What's unclear: LaunchAgent hotkeys require permission for the app launchd uses to run Saymo, not always the current terminal.
   - Recommendation: Split terminal/Chrome/provider permission guidance from LaunchAgent hotkey guidance in tests so actions are exact.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest installed `9.0.3` |
| Config file | `pyproject.toml` dependency group only; no pytest config detected |
| Quick run command | `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py tests/test_dry_run_cli.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ENV-01 | Dry-run contains provider tab, Chrome/provider state, configured capture/playback, BlackHole 2ch/16ch, recording mic, and dry-run reruns/actions. | unit + CLI | `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_dry_run_cli.py -q` | ✅ extend existing files |
| ENV-02 | Dry-run contains LaunchAgent install/load/plist currency, daemon heartbeat/running, hotkey status, stale plist status, log paths, and exact status/start/restart/probe commands. | unit + CLI | `uv run pytest tests/analysis/test_launch_agent.py tests/analysis/test_launch_readiness.py tests/test_call_control_cli.py -q` | ✅ extend existing files |
| ENV-03 | Dry-run does not activate providers, toggle mute, switch microphones, play/record audio, write audio config, run lifecycle launchctl commands, or call call-control probe. | static + unit | `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_provider_audio_readiness.py tests/test_call_control_cli.py -q` | ✅ extend existing files |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py tests/test_dry_run_cli.py -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/analysis/test_provider_audio_readiness.py` - add dry-run rerun/action coverage for provider tab, audio devices, provider capabilities, and permission checks.
- [ ] `tests/analysis/test_launch_readiness.py` - assert `collect_launch_readiness(..., mode="dry-run")` passes dry-run context into provider/audio collectors and preserves check order.
- [ ] `tests/analysis/test_launch_agent.py` - add focused action/rerun assertions for not-installed, installed-not-loaded, plist drift, stale heartbeat, crash loop, hotkey permission blocked, and running states as consumed by launch readiness.
- [ ] `tests/test_call_control_cli.py` - keep status JSON read-only and ensure status/probe/lifecycle command separation remains clear.
- [ ] `tests/test_dry_run_cli.py` - extend static guard to forbid launchd lifecycle mutators, provider mutators, audio streams, `run_handbrake_reachability_probe`, `commands.jsonl`, and `audit.jsonl` writes in dry-run.
- [ ] Docs tests if docs are changed: `tests/test_live_control_docs.py` and `tests/test_launch_realtime_evidence_docs.py`.

## Sources

### Primary (HIGH confidence)

- Local code: `saymo/analysis/provider_audio_readiness.py` - existing provider/audio collection, BlackHole device constants, metadata, non-destructive permission probes.
- Local code: `saymo/analysis/launch_readiness.py` - shared dry-run/call-ready orchestration, renderer, sanitizer, call-control integration.
- Local code: `saymo/analysis/launch_agent.py` - LaunchAgent spec, plist hashing, read-only status classification, lifecycle command boundaries.
- Local code: `saymo/analysis/control_daemon.py` - heartbeat freshness and explicit reachability probe behavior.
- Local tests: `tests/analysis/test_provider_audio_readiness.py`, `tests/analysis/test_launch_readiness.py`, `tests/analysis/test_launch_agent.py`, `tests/test_call_control_cli.py`, `tests/test_dry_run_cli.py` - current safety and contract patterns.
- Project docs: `docs/LIVE-CONTROL-HANDBRAKE.md`, `docs/LAUNCH-REALTIME-EVIDENCE.md` - operator commands, logs, read-only evidence and privacy boundaries.
- Apple Developer Archive, Creating Launch Daemons and Agents - verified per-user agents, plist keys/log paths, launchd process guidance: https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
- python-sounddevice docs - verified `query_devices`, `check_input_settings`, `check_output_settings` behavior: https://python-sounddevice.readthedocs.io/en/latest/api/checking-hardware.html
- Python `plistlib` docs - verified plist generation/parsing APIs and XML output support: https://docs.python.org/3/library/plistlib.html
- Click testing docs - verified `CliRunner.invoke` and exit/output testing pattern: https://click.palletsprojects.com/en/stable/testing/
- pytest monkeypatch docs - verified monkeypatch boundary-testing pattern: https://docs.pytest.org/en/stable/how-to/monkeypatch.html

### Secondary (MEDIUM confidence)

- PyPI JSON registry metadata via `curl` for current package versions and publish timestamps.

### Tertiary (LOW confidence)

- None used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - derived from `pyproject.toml`, installed package metadata, PyPI JSON, and official docs.
- Architecture: HIGH - derived from current local code/tests and Phase 48/49 verified contracts.
- Pitfalls: HIGH - most pitfalls are already represented by existing tests or explicit Phase 50 constraints.

**Research date:** 2026-07-10
**Valid until:** 2026-08-09 for project architecture; recheck PyPI versions before dependency planning.
