---
phase: 37-provider-and-audio-remediation
verified: 2026-07-08T15:10:41Z
status: passed
verdict: PASS
score: 5/5 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 4/5 requirements verified
  gaps_closed:
    - "Default microphone-capture permission detection now uses already-discovered recording microphone route metadata and sounddevice.check_input_settings."
    - "Default audio-routing permission detection now reuses audio route checks and sounddevice.check_input_settings/check_output_settings for configured capture, playback, and BlackHole routes."
    - "Chrome provider readiness now opts into strict AppleScript errors so osascript permission denial reaches provider readiness and becomes chrome_automation_permission."
    - "Regression tests now prove default collect_provider_audio_checks emits Chrome, microphone, and audio-routing permission rows without injected permission flags."
  gaps_remaining: []
  regressions: []
---

# Phase 37: Provider and Audio Remediation Verification Report

**Phase Goal:** User can verify provider, Chrome tab, BlackHole routing, microphone takeover, and macOS permission readiness without destructive provider or system audio actions.
**Verified:** 2026-07-08T15:10:41Z
**Status:** PASS
**Re-verification:** Yes - after PROV-04 blocker fixes

## Goal Achievement

Phase 37 now satisfies the goal and closes the previous PROV-04 blocker. Provider tab readiness, audio route visibility, provider capability reporting, macOS permission remediation, and non-destructive default behavior are present, substantive, wired into `call-ready`, and covered by fresh automated verification.

## Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User can see whether the configured provider and Chrome meeting tab are present, identifiable, actionable, and safe before realtime mode. | VERIFIED | `collect_provider_audio_checks()` starts with `provider_meeting_tab`; `_provider_tab_check_with_context()` resolves providers and calls only `provider.check_ready()`; metadata includes provider, configured provider, URL pattern, meeting state, app state, and tab info. CLI and artifact tests cover the row. |
| 2 | User can verify BlackHole capture/playback routing and the real microphone takeover route before joining or starting the live loop. | VERIFIED | `collect_audio_route_checks()` emits `capture_input_device`, `playback_output_device`, `provider_output_blackhole`, `capture_route_blackhole`, and `recording_microphone_input` using `audio_devices.find_device()` with explicit input/output kind. |
| 3 | User can see provider capability limits without provider actions or raw-error parsing. | VERIFIED | `provider_capabilities` reports tab activation, mute recovery, mic-switch support/status, and limitations; tests assert provider mutators are not called. |
| 4 | User can see macOS permission blockers for hotkeys, microphone capture, Chrome automation, and audio routing with targeted remediation. | VERIFIED | Hotkey doctor remains wired. Chrome permission text from strict provider readiness maps to `chrome_automation_permission`. Default microphone/audio-routing probes reuse route checks and emit `microphone_capture_permission` / `audio_routing_permission` when `sounddevice.check_*_settings` raises. |
| 5 | User can run provider/audio readiness with no destructive Chrome, meeting, recording, playback, config, route, or volume changes. | VERIFIED | Production grep found no provider mutators, playback, recording, config write, volume, route, kill, or `subprocess.run` calls in the default provider/audio readiness path. Tests patch those APIs as forbidden. |

**Score:** 5/5 must-haves verified

## Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Configured provider and Chrome meeting tab are present, identifiable, actionable, and safe to use before realtime mode. | VERIFIED | `provider_meeting_tab` row is wired into launch readiness and call-ready artifacts. |
| 2 | BlackHole capture/playback routing and real microphone takeover route are verified before joining or starting the live loop. | VERIFIED | Five audio route rows are emitted without changing system defaults or provider state. |
| 3 | Provider capability limits, activation support, mic switching support, mute recovery, and unsupported-provider blockers are visible without raw errors. | VERIFIED | `provider_capabilities` exposes supported/unsupported capability metadata and remediation. |
| 4 | Provider/audio readiness has targeted permission remediation and no destructive Chrome, meeting, or system-route changes. | VERIFIED | Permission rows are default-detected with safe probes; non-destructive tests and greps passed. |

## Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `saymo/analysis/provider_audio_readiness.py` | Provider tab, audio route, capability, and permission checks | VERIFIED | Main collector reuses route checks for permission probes; `_check_device_settings_blocked()` calls only `sd.check_input_settings` / `sd.check_output_settings`. |
| `saymo/glip_control.py` | AppleScript helper exposes permission-denial errors when requested | VERIFIED | `AppleScriptError` exists; `_run_applescript(..., raise_on_error=False)` preserves default non-raising behavior; strict mode raises only when opted in. |
| `saymo/providers/_chrome_base.py` | Provider readiness propagates Chrome Automation denial | VERIFIED | `ChromeCallProvider.check_ready()` calls `_run_applescript(..., raise_on_error=True)` for tab discovery. |
| `saymo/analysis/launch_readiness.py` | Shared launch collector wires provider/audio checks and artifact serialization | VERIFIED | Phase 37 rows appear after cloned-voice metadata in call-ready artifacts and `_LAUNCH_CHECK_ORDER`. |
| `saymo/analysis/remediation.py` | Provider/audio/permission remediation categories | VERIFIED | Tests cover `[provider]`, `[audio-device]`, and `[macos-permission]` categories. |
| `saymo/commands/call_ready.py` | CLI surfaces human, JSON, and output artifact provider/audio rows | VERIFIED | `--json` and `--output` use the shared report; live smoke artifact contained provider/audio rows. |
| `tests/analysis/test_provider_audio_readiness.py` | PROV-01 through PROV-05 helper coverage | VERIFIED | Includes default permission blocker detection without injected permission flags and non-destructive assertions. |
| `tests/test_glip_control.py` | Strict AppleScript behavior | VERIFIED | Covers default non-strict return and strict `AppleScriptError` raising. |
| `tests/test_call_ready_cli.py` | CLI artifact and non-destructive coverage | VERIFIED | Covers provider/audio keys, artifact output, remediation grouping, and forbidden mutator APIs. |

## Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `saymo/analysis/launch_readiness.py` | `collect_provider_audio_checks()` | Launch collector import plus check extension | WIRED | Provider/audio checks are in the shared call-ready report and artifact. |
| `collect_provider_audio_checks()` | `collect_audio_route_checks()` | `audio_route_checks` tuple passed into permission checks | WIRED | Permission checks reuse the exact route metadata already discovered by the route checks. |
| `collect_permission_checks()` | Chrome Automation remediation | `provider_error` and `_looks_like_chrome_permission_error()` | WIRED | Strict AppleScript denial from provider readiness becomes `chrome_automation_permission`. |
| `collect_permission_checks()` | Hotkey Accessibility remediation | `live_control.build_hotkey_doctor_report(..., probe=True)` | WIRED | Non-ok hotkey registration produces `hotkey_accessibility_permission`. |
| `collect_permission_checks()` | Microphone capture remediation | `_microphone_permission_blocked()` plus `sd.check_input_settings` | WIRED | Default path emits `microphone_capture_permission` when safe input settings probe raises. |
| `collect_permission_checks()` | Audio routing remediation | `_audio_routing_permission_blocked()` plus `sd.check_input_settings` / `sd.check_output_settings` | WIRED | Default path emits `audio_routing_permission` when safe route settings probe raises. |
| `ChromeCallProvider.check_ready()` | `_run_applescript(..., raise_on_error=True)` | Opt-in strict mode | WIRED | Permission-denied osascript failures are no longer swallowed by provider readiness. |

## Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| PROV-01 | VERIFIED | `provider_meeting_tab` reports provider identity, configured provider, URL pattern, app/meeting state, tab info, actions, and rerun. |
| PROV-02 | VERIFIED | Audio route rows verify configured capture/playback devices, BlackHole provider output, BlackHole capture route, and configured recording microphone input. |
| PROV-03 | VERIFIED | `provider_capabilities` reports activation, mute recovery, mic switching support/status, and limitations. |
| PROV-04 | VERIFIED | Default call-ready permission path now covers Chrome Automation, hotkey Accessibility, microphone capture, and audio routing with targeted remediation rows. |
| PROV-05 | VERIFIED | Default provider/audio readiness avoids destructive provider, Chrome, playback, recording, config, system-route, and volume mutations. |

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| none | - | - | - | No blocker anti-patterns found in the Phase 37 production path. |

## Verification Commands

| Command | Result |
| --- | --- |
| `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_collect_provider_audio_checks_detects_default_permission_blockers tests/test_glip_control.py::test_run_applescript_strict_mode_exposes_permission_errors -q` | `2 passed in 0.15s` |
| `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/test_hotkey_doctor.py tests/analysis/test_remediation.py tests/test_glip_control.py -q` | `32 passed in 2.32s` |
| `uv run pytest` | `443 passed in 5.43s` |
| `rg -n "provider_audio_basic_scope|basic_provider_audio_placeholder" saymo/analysis tests/analysis tests/test_call_ready_cli.py` | no matches |
| `rg -n "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill|subprocess\\.run" saymo/analysis/provider_audio_readiness.py saymo/analysis/launch_readiness.py saymo/commands/call_ready.py` | no matches |
| `rg -n "check_input_settings|check_output_settings|sounddevice\\.rec|sd\\.rec|play_audio_bytes|play_bytes_to_devices|set_input_volume|bump_input_volume|_write_audio_settings_to_user_config" saymo/analysis/provider_audio_readiness.py tests/analysis/test_provider_audio_readiness.py tests/test_call_ready_cli.py` | production matches only `sd.check_output_settings` and `sd.check_input_settings`; destructive APIs appear only as forbidden test patches |
| `git diff --check` | passed |
| `uv run saymo call-ready -p standup --provider glip --output /tmp/saymo-phase37-call-ready-verification.json` | returned rc=1 as expected for local state; artifact contained Phase 37 provider/audio rows, no permission rows, and blockers only for local source placeholder, missing prepared audio, and missing Glip tab |

## Residual Risks

| Risk | Status | Mitigation |
| --- | --- | --- |
| Real macOS TCC permission denial behavior varies by terminal app and host state. | Residual, non-blocking | Automated tests simulate denial at the provider and sounddevice probe boundaries; live manual TCC denial checks can still be useful before relying on a new machine. |
| `sounddevice.check_input_settings` / `check_output_settings` are safe status probes, not full recording/playback checks. | Accepted by phase scope | The phase explicitly requires non-destructive readiness; recording/playback remains behind explicit diagnostic commands. |
| Default `_run_applescript()` remains non-strict for legacy helpers. | Intentional | Strict propagation is scoped to provider readiness through `raise_on_error=True`; existing mutating helper behavior is preserved. |

## Human Verification Required

None required to pass this re-verification. Optional live checks can revoke Chrome Automation or microphone permission on a test machine and confirm the same permission rows appear in `saymo call-ready`.

## Gaps Summary

No remaining gaps. The previous PROV-04 blocker is closed without introducing destructive default behavior.

---

_Verified: 2026-07-08T15:10:41Z_
_Verifier: Claude (gsd-verifier)_
