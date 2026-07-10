---
phase: 50-provider-audio-and-call-control-health
verified: 2026-07-10T14:11:37Z
status: human_needed
score: "5/5 must-haves verified"
human_verification:
  - test: "Live provider/audio/control dry-run on macOS"
    expected: "saymo dry-run -p <profile> --provider <provider> reports provider tab, Chrome/provider state, capture/playback devices, BlackHole routes, recording microphone, and call-control health without changing call or audio state."
    why_human: "The automated suite monkeypatches Chrome, sounddevice, BlackHole, launchctl, heartbeat, and hotkey boundaries; actual local OS state needs an operator run."
  - test: "Live blocker remediation wording"
    expected: "With a missing meeting tab, missing device, or unhealthy LaunchAgent, dry-run shows explicit manual commands such as saymo test-devices, call-control-agent install/start/restart/status, and call-control probe."
    why_human: "Automated tests prove string contracts, but final operator clarity depends on real terminal output in the user's environment."
  - test: "Live no-auto-repair observation"
    expected: "Running dry-run does not focus Chrome, activate a meeting, toggle mute, switch microphone/devices, play/record audio, write call-control command/audit logs, or mutate launchd."
    why_human: "Static and unit tests prove forbidden code paths are absent, but only a live run can observe surrounding OS/app state."
---

# Phase 50: Provider, Audio, And Call-Control Health Verification Report

**Phase Goal:** User can prove provider, Chrome tab, BlackHole routing, playback/capture devices, and call-control LaunchAgent health before joining a call, while repairs remain explicit.
**Verified:** 2026-07-10T14:11:37Z
**Status:** human_needed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User can run `saymo dry-run -p <profile> --provider <provider>` and see provider tab, Chrome/provider state, configured capture/playback devices, BlackHole output/input routes, and real recording microphone readiness in one dry-run result. | VERIFIED | `dry_run.py` calls `collect_launch_readiness(..., mode="dry-run")`; `launch_readiness.py` forwards dry-run context to provider/audio checks; `provider_audio_readiness.py` returns provider tab plus five audio route rows. |
| 2 | User can see dry-run provider/audio blocker actions and reruns that point to explicit manual steps or commands. | VERIFIED | Missing audio routes recommend `saymo test-devices` and config edits; dry-run reruns are threaded via `rerun_command`; provider errors use dry-run wording. |
| 3 | User can see call-control LaunchAgent install/load/plist currency, daemon heartbeat/running state, hotkey registration state, log paths, and exact install/start/restart/status/probe commands before joining a call. | VERIFIED | `launch_agent.py` classifies not installed, plist drift, unloaded, stale heartbeat, crash loop, hotkey permission, and running states; `launch_readiness.py` emits agent/daemon/hotkey rows with log-path metadata and status/probe reruns. |
| 4 | User can trust dry-run diagnostics to remain read-only. | VERIFIED | Production safety grep found no provider mutators, audio playback/recording/config writers, call-control probe execution, or LaunchAgent lifecycle helper calls in dry-run/readiness files. Tests also monkeypatch forbidden helpers to fail if invoked. |
| 5 | Existing `saymo call-ready` provider/audio/control defaults and older tests remain backward compatible. | VERIFIED | Provider/audio collectors default to call-ready reruns; launch readiness only forwards new provider/audio kwargs when dry-run context is supported; focused Phase 50 tests pass. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `saymo/commands/dry_run.py` | CLI entry point for one dry-run command | VERIFIED | Calls shared launch readiness with `mode="dry-run"` and only writes a sanitized artifact when `--output` is explicit. |
| `saymo/analysis/launch_readiness.py` | Shared dry-run/call-ready orchestration, provider/audio wiring, call-control rows | VERIFIED | `_launch_rerun_command()` produces dry-run reruns; `_collect_phase36_checks()` wires provider/audio; `_collect_call_control_checks()` reads status and emits agent/daemon/hotkey rows. |
| `saymo/analysis/provider_audio_readiness.py` | Provider tab, Chrome/provider metadata, capture/playback/BlackHole/recording microphone checks, explicit actions | VERIFIED | Collectors accept optional `rerun_command`/`mode`, return shared `LaunchReadinessCheck` rows, and use `audio_devices.find_device` plus `sounddevice.check_*_settings` only. |
| `saymo/analysis/launch_agent.py` | Read-only LaunchAgent, heartbeat, hotkey classification and exact action text | VERIFIED | Status path reads plist/hash/plutil/launchctl print/heartbeat evidence and maps classifications to install/start/restart/status guidance. Lifecycle helpers exist but are not wired into dry-run/readiness. |
| `saymo/commands/call_control.py` | Explicit status/probe/lifecycle command boundary | VERIFIED | `status` calls `collect_call_control_agent_status`; `probe` and lifecycle operations are separate explicit CLI commands. |
| `tests/analysis/test_provider_audio_readiness.py` | Provider/audio dry-run contracts and safety tests | VERIFIED | Includes dry-run context, safe metadata, call-ready compatibility, and non-destructive provider/audio assertions. |
| `tests/analysis/test_launch_readiness.py` | Launch-readiness provider/audio and call-control wiring tests | VERIFIED | Includes dry-run provider/audio context forwarding and status-only call-control scenarios. |
| `tests/analysis/test_launch_agent.py` | LaunchAgent action/rerun command tests | VERIFIED | Pins exact install/start/restart/status action strings across classifications. |
| `tests/test_dry_run_cli.py` | CLI dry-run and static no-auto-repair guard | VERIFIED | Static forbidden-reference list covers provider mutators, audio/TTS paths, probe execution, launchd lifecycle helpers, and command/audit logs. |
| `tests/test_call_control_cli.py` | Call-control status/probe/lifecycle separation tests | VERIFIED | Status JSON records only plutil lint and launchctl print, and does not create command/audit logs. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `saymo/commands/dry_run.py` | `collect_launch_readiness` | `mode="dry-run"` | WIRED | The dry-run command invokes shared readiness with dry-run mode and exits 0/1 from `report.ready`. |
| `saymo/analysis/launch_readiness.py` | `collect_provider_audio_checks` | `rerun_command=_launch_rerun_command(...)`, `mode=mode` | WIRED | Dry-run provider/audio checks receive `saymo dry-run -p <profile> --provider <provider>` when the collector supports the new context. |
| `saymo/analysis/provider_audio_readiness.py` | shared `LaunchReadinessCheck` | provider/audio collector return rows | WIRED | Provider tab, capture input, playback output, BlackHole output/input, recording microphone, capability, and permission rows use the shared contract. |
| `saymo/analysis/launch_readiness.py` | `collect_call_control_agent_status` | `_collect_call_control_checks()` | WIRED | Launch readiness calls status only and maps returned status to agent, daemon, and hotkey readiness rows. |
| `saymo/analysis/launch_agent.py` | macOS status evidence | `plutil_lint_argv`, `print_argv`, heartbeat read | WIRED | Status classification reads plist, launchctl print, heartbeat, and hotkey evidence without lifecycle mutation calls. |
| `tests/test_dry_run_cli.py` | `saymo.commands.dry_run` | static forbidden-reference scan | WIRED | The static guard prevents dry-run from importing or referencing known repair/mutation APIs. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| ENV-01 | 50-01, 50-02 | User can verify provider tab readiness, Chrome/provider state, BlackHole capture/playback devices, and audio routing prerequisites in one dry-run result. | SATISFIED | Provider/audio collector returns provider tab and five audio route rows with dry-run reruns; tests cover metadata and row order. |
| ENV-02 | 50-01, 50-02 | User can verify call-control daemon and LaunchAgent health, including heartbeat freshness, hotkey availability, stale plist status, and exact restart/probe commands. | SATISFIED | LaunchAgent status classification and launch-readiness call-control rows include install/load/plist, heartbeat/running, hotkey status, log paths, status reruns, and probe guidance. |
| ENV-03 | 50-01, 50-02 | User can keep provider repair explicit; dry-run diagnostics may suggest safe commands but must not kill apps, change meeting state, or switch devices automatically. | SATISFIED | Static grep over production dry-run/readiness files found no forbidden provider/audio/control mutation references; tests assert dry-run and status paths are read-only. |

No Phase 50 requirements are orphaned: `ENV-01`, `ENV-02`, and `ENV-03` appear in both Phase 50 plans and in `.planning/REQUIREMENTS.md`.

### Command Evidence

| Command | Result |
| --- | --- |
| `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/analysis/test_launch_agent.py tests/test_dry_run_cli.py tests/test_call_control_cli.py -q` | `54 passed in 1.50s` |
| Static safety grep over `saymo/analysis/provider_audio_readiness.py`, `saymo/analysis/launch_readiness.py`, `saymo/commands/dry_run.py` for provider mutators, playback/recording, config/audio-volume writers, probe execution, and LaunchAgent lifecycle helpers | No matches |
| `git diff --check` | Clean |
| `git status --short` | Clean before creating this verification report |
| Orchestrator-provided full-suite evidence | `uv run pytest -q` -> `635 passed`; expanded Phase 50 regression set -> `63 passed`; static safety grep -> `STATIC_SAFETY_OK` |

### Safety Boundary Findings

| Boundary | Status | Evidence |
| --- | --- | --- |
| Provider/Chrome | VERIFIED | Provider readiness calls `provider.check_ready()` and metadata inspection; tests assert `activate_meeting`, `toggle_mute`, `switch_mic`, `get_previous_app`, and `activate_app` are not called. |
| Audio routing | VERIFIED | Audio readiness uses device discovery and `sounddevice.check_input_settings` / `check_output_settings`; static grep found no playback, recording, or audio config writer references in dry-run/readiness files. |
| Call-control probe | VERIFIED | Dry-run/readiness recommend `saymo call-control probe -p <profile>` as text only; `run_handbrake_reachability_probe` is absent from dry-run/readiness production files. |
| LaunchAgent lifecycle | VERIFIED | Lifecycle helpers remain explicit CLI commands; dry-run/readiness status path does not call install/start/stop/restart/uninstall/bootstrap/bootout/kickstart. |
| Sanitization | VERIFIED | `LaunchReadinessCheck.to_dict()` and tests redact private sentinels/secrets from serialized output. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `tests/test_dry_run_cli.py` | 154 | `placeholder_only` | Info | Test fixture for source-readiness blocker, not a stub. |
| `tests/analysis/test_launch_readiness.py` | 416 | placeholder daily-note test | Info | Expected source-readiness scenario, not incomplete Phase 50 implementation. |
| production files | n/a | TODO/FIXME/stub/placeholder scan | None | No blocker or warning anti-patterns found in Phase 50 production files. |

### Human Verification Required

### 1. Live Provider/Audio/Control Dry-Run

**Test:** On the target macOS machine, run `saymo dry-run -p <profile> --provider <provider>` with the intended Chrome/provider tab and audio setup.
**Expected:** Output includes provider tab, Chrome/provider state, configured capture/playback devices, BlackHole 2ch/16ch routes, recording microphone, call-control agent, daemon, and hotkey rows.
**Why human:** Unit tests monkeypatch Chrome, sounddevice, BlackHole, launchctl, heartbeat, and hotkey status. Actual local OS state needs a live operator run.

### 2. Live Blocker Remediation Wording

**Test:** Run dry-run in a safe intentionally-not-ready state, such as no meeting tab or stopped/missing call-control agent.
**Expected:** Output stays explicit and actionable, with manual steps or commands and reruns instead of auto-repair.
**Why human:** Automated tests pin command strings, but final usefulness depends on real terminal output with the user's configured profile/provider.

### 3. Live No-Auto-Repair Observation

**Test:** Observe Chrome, audio input/output selections, call state, `~/.saymo/live_control/<profile>/commands.jsonl`, `audit.jsonl`, and launchd state before and after dry-run.
**Expected:** Dry-run does not focus Chrome, activate/join/change the meeting, toggle mute, switch mic/devices, play/record audio, queue control commands, write audit logs, or mutate LaunchAgent lifecycle state.
**Why human:** Static/unit verification proves forbidden code references are absent, but OS/app state must be observed live for final confidence.

### Gaps Summary

No automated code gaps were found. The implementation satisfies all five Phase 50 must-haves and all mapped Phase 50 requirements. Status is `human_needed` only because the final proof involves live macOS/Chrome/BlackHole/LaunchAgent state that cannot be fully verified from static code and monkeypatched tests.

---

_Verified: 2026-07-10T14:11:37Z_
_Verifier: Claude (gsd-verifier)_
