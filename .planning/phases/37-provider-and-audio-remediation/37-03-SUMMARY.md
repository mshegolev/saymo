---
phase: 37-provider-and-audio-remediation
plan: "03"
subsystem: launch-readiness
tags: [saymo, call-ready, provider-capabilities, macos-permissions, remediation, pytest]

requires:
  - phase: 36-call-ready-preflight-and-cache-gate
    provides: shared LaunchReadinessCheck contract, call-ready CLI, JSON artifact path, and grouped remediation
  - phase: 37-provider-and-audio-remediation
    plan: "01"
    provides: provider meeting tab readiness helper and non-destructive provider check pattern
  - phase: 37-provider-and-audio-remediation
    plan: "02"
    provides: read-only audio route checks and audio-device remediation metadata
provides:
  - Provider capability readiness rows for tab activation, mute recovery, and microphone switching support
  - Non-destructive macOS permission remediation rows for Chrome automation, hotkey Accessibility, microphone capture, and audio routing blockers
  - Provider, audio-device, and macos-permission remediation category mappings for launch readiness
affects: [phase-37, phase-38, phase-39, call-ready, launch-gate, provider-readiness, audio-routing]

tech-stack:
  added: []
  patterns:
    - Capability checks inspect provider class/attribute metadata without invoking provider actions
    - Permission checks emit explicit macOS remediation rows only from safe status/error signals
    - Launch remediation categories are derived from LaunchReadinessCheck keys and metadata

key-files:
  created:
    - .planning/phases/37-provider-and-audio-remediation/37-03-SUMMARY.md
  modified:
    - saymo/analysis/provider_audio_readiness.py
    - saymo/analysis/remediation.py
    - tests/analysis/test_provider_audio_readiness.py
    - tests/analysis/test_remediation.py
    - tests/analysis/test_launch_readiness.py
    - tests/test_call_ready_cli.py

key-decisions:
  - "Provider capability checks are metadata-only; they never call activate_meeting, toggle_mute, switch_mic, focus restore, playback, recording, or route mutation helpers."
  - "Glip and MTS Link microphone switching support is detected from provider class/override structure; generic Chrome-style providers surface mic_switch_unsupported as a warning row."
  - "Missing hotkey bindings are not treated as a macOS permission blocker; hotkey Accessibility rows are reserved for blocked or unavailable registration probes."

patterns-established:
  - "Permission rows use category=macos-permission, explicit check keys, exact action text, and call-ready rerun commands."
  - "collect_provider_audio_checks returns provider tab, audio routes, provider capabilities, then permission rows."

requirements-completed: [PROV-03, PROV-04, PROV-05]

duration: 7 min
completed: 2026-07-08
---

# Phase 37 Plan 03: Provider Capability and Permission Readiness Summary

**Provider capability limits and macOS permission blockers now appear as categorized, non-destructive call-ready remediation.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-08T14:29:38Z
- **Completed:** 2026-07-08T14:36:40Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added `collect_provider_capability_checks()` with metadata for tab activation, mute recovery, mic switch support/status, and capability limitations.
- Added `collect_permission_checks()` with explicit `chrome_automation_permission`, `hotkey_accessibility_permission`, `microphone_capture_permission`, and `audio_routing_permission` blocker rows.
- Extended `collect_provider_audio_checks()` to append capability and permission rows after provider tab and audio route rows.
- Updated launch remediation mapping and CLI expectations for `[provider]`, `[audio-device]`, and `[macos-permission]` output.

## Task Commits

1. **Task 1 RED: Capability and permission readiness tests** - `15d4661` (`test`)
2. **Task 2 GREEN: Capability, permission, and remediation checks** - `7e6e5d9` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/provider_audio_readiness.py` - Adds provider capability checks, macOS permission rows, and integrates them into provider/audio readiness.
- `saymo/analysis/remediation.py` - Maps provider, audio-device, and macos-permission launch check keys to grouped remediation categories.
- `tests/analysis/test_provider_audio_readiness.py` - Adds RED/GREEN coverage for capabilities, permission blocker rows, and non-destructive behavior.
- `tests/analysis/test_remediation.py` - Adds launch category mapping coverage for provider/audio/permission checks.
- `tests/analysis/test_launch_readiness.py` - Aligns existing grouped remediation expectations with the new provider category.
- `tests/test_call_ready_cli.py` - Extends grouped remediation output fixture to include provider, audio-device, and macos-permission rows.
- `.planning/phases/37-provider-and-audio-remediation/37-03-SUMMARY.md` - Execution summary.

## Decisions Made

- Capability support is detected from provider structure only; no provider method is invoked.
- Microphone capture and audio routing permission rows are explicit blockers when a safe probe or test hook reports blocked; default helpers remain conservative and non-mutating.
- `build_hotkey_doctor_report(config, profile, probe=True)` is called through the `saymo.analysis.live_control` module so tests can monkeypatch it.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_provider_audio_readiness.py::test_provider_capabilities_are_reported_without_actions tests/analysis/test_provider_audio_readiness.py::test_permission_blockers_are_actionable tests/analysis/test_remediation.py::test_launch_provider_audio_hints_classify_permissions -q; test $? -ne 0'`
  - RED result: command exited 0 after the expected failures, `3 failed in 0.29s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_provider_capabilities_are_reported_without_actions tests/analysis/test_provider_audio_readiness.py::test_permission_blockers_are_actionable tests/analysis/test_remediation.py::test_launch_provider_audio_hints_classify_permissions -q`
  - Result: `3 passed in 0.29s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/analysis/test_remediation.py -q`
  - Result: `25 passed in 1.51s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/test_hotkey_doctor.py tests/analysis/test_remediation.py -q`
  - Result: `29 passed in 1.53s`.
- `git diff --check`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/provider_audio_readiness.py'`
  - Result: passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Contract] Updated existing remediation expectations for new provider category**
- **Found during:** Task 2 phase-focused verification.
- **Issue:** Existing launch remediation tests still expected `provider_meeting_tab` to group under `[retest]`, and the non-destructive provider/audio test expected only provider-tab plus audio-route rows.
- **Fix:** Updated the affected tests to expect `[provider] provider meeting tab` and the appended `provider_capabilities` row.
- **Files modified:** `tests/analysis/test_launch_readiness.py`, `tests/analysis/test_provider_audio_readiness.py`
- **Verification:** Focused, phase-focused, and wave validation commands passed.
- **Committed in:** `7e6e5d9`

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** No scope expansion; the fix aligns pre-existing tests with the new launch remediation contract.

## Issues Encountered

Phase-focused verification initially failed only on the two existing expectations documented above. Production behavior did not require a design change.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 37-04 can integrate and verify the full provider/audio readiness surface knowing provider capabilities and macOS permission blockers now produce categorized, non-destructive launch rows.

## Self-Check: PASSED

- Created/modified files found: `saymo/analysis/provider_audio_readiness.py`, `saymo/analysis/remediation.py`, `tests/analysis/test_provider_audio_readiness.py`, `tests/analysis/test_remediation.py`, `tests/analysis/test_launch_readiness.py`, `tests/test_call_ready_cli.py`, and this summary.
- Task commits found: `15d4661` and `7e6e5d9`.
- Required focused, phase-focused, and wave verification results are recorded above.

---
*Phase: 37-provider-and-audio-remediation*
*Completed: 2026-07-08*
