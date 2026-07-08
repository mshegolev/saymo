---
phase: 37-provider-and-audio-remediation
plan: "04"
subsystem: launch-readiness
tags: [saymo, call-ready, provider-audio, non-destructive, artifacts, pytest]

requires:
  - phase: 36-call-ready-preflight-and-cache-gate
    provides: shared LaunchReadinessCheck contract, call-ready CLI, JSON artifact path, and grouped remediation
  - phase: 37-provider-and-audio-remediation
    plan: "01"
    provides: provider meeting tab readiness and read-only provider check pattern
  - phase: 37-provider-and-audio-remediation
    plan: "02"
    provides: read-only audio route checks for BlackHole and recording microphone visibility
  - phase: 37-provider-and-audio-remediation
    plan: "03"
    provides: provider capability and macOS permission readiness rows
provides:
  - End-to-end CLI regression coverage proving default call-ready provider/audio checks do not mutate provider, audio, config, Chrome, or macOS state
  - Sanitized call-ready output artifact coverage for provider tab, audio route, capability, and permission rows
  - Final Phase 37 launch order coverage after cloned voice metadata with the old placeholder removed
affects: [phase-37, phase-38, phase-39, call-ready, launch-gate, provider-readiness, audio-routing]

tech-stack:
  added: []
  patterns:
    - CLI non-destructive tests guard provider mutators, playback, recording, config writes, volume changes, and Chrome kill commands
    - Output artifact assertions use LaunchReadinessReport.to_dict through the real call-ready command path
    - Fixed provider/audio rows are ordered before conditional macOS permission rows

key-files:
  created:
    - .planning/phases/37-provider-and-audio-remediation/37-04-SUMMARY.md
  modified:
    - saymo/analysis/launch_readiness.py
    - tests/analysis/test_launch_readiness.py
    - tests/test_call_ready_cli.py

key-decisions:
  - "Default call-ready provider/audio behavior is now asserted at the CLI boundary with mocked provider, audio, and permission helpers."
  - "The static launch order tracks the fixed provider/audio sequence after cloned_voice_metadata; permission rows remain conditional and follow that sequence when emitted."
  - "Call-ready --output artifacts continue to use sanitized LaunchReadinessReport.to_dict output instead of a separate artifact renderer."

patterns-established:
  - "Provider/audio artifact tests run through the real click command and patch only external readiness dependencies."
  - "Removed placeholder coverage uses dynamic old-key construction in tests so grep can enforce that stale placeholder tokens are absent from source and tests."

requirements-completed: [PROV-01, PROV-02, PROV-03, PROV-04, PROV-05]

duration: 11 min
completed: 2026-07-08
---

# Phase 37 Plan 04: Provider and Audio Safety Proof Summary

**Call-ready provider/audio checks are now proven non-destructive and artifact-safe across helper, CLI, grep, wave, and full-suite validation.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-07-08T14:42:14Z
- **Completed:** 2026-07-08T14:53:09Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added CLI-level safety regression coverage proving default `saymo call-ready` does not call provider mutators, playback, recording, config writes, macOS volume mutation, or Chrome kill commands.
- Added `--output` artifact regression coverage for provider tab, capture/playback devices, BlackHole routing, recording microphone, provider capabilities, and permission rows with private sentinels redacted.
- Updated launch-readiness order coverage so Phase 37 provider/audio rows follow `cloned_voice_metadata` and the old provider/audio placeholder is absent.

## Task Commits

1. **Task 1 RED: End-to-end safety and artifact regressions** - `663aa95` (`test`)
2. **Task 2 GREEN: Launch order hardening and validation** - `af3e37c` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/launch_readiness.py` - Lists the fixed Phase 37 provider/audio sequence in the launch order constant.
- `tests/analysis/test_launch_readiness.py` - Verifies provider/audio rows follow cloned voice metadata and conditional permission rows follow the fixed sequence.
- `tests/test_call_ready_cli.py` - Adds CLI non-destructive and sanitized artifact regressions, and removes stale placeholder fixture expectations.
- `.planning/phases/37-provider-and-audio-remediation/37-04-SUMMARY.md` - Execution summary.

## Decisions Made

- The non-destructive proof is enforced at the click command boundary, not only in helper tests.
- Provider/audio ordering is split into fixed rows and conditional permission rows, because permission checks appear only when blockers are detected.
- Existing explicit mutating diagnostics remain separate commands; `takeover-check` and `hotkey-doctor` tests stayed green in the wave suite.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_provider_audio_readiness.py::test_collect_provider_audio_checks_is_non_destructive tests/test_call_ready_cli.py::test_call_ready_provider_audio_checks_are_non_destructive tests/test_call_ready_cli.py::test_call_ready_output_artifact_includes_provider_audio_checks -q; test $? -ne 0'`
  - RED result: command exited 0 after the expected failure, `1 failed, 2 passed in 0.61s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_collect_provider_audio_checks_is_non_destructive tests/test_call_ready_cli.py::test_call_ready_provider_audio_checks_are_non_destructive tests/test_call_ready_cli.py::test_call_ready_output_artifact_includes_provider_audio_checks -q`
  - Result: `3 passed in 0.54s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
  - Result: `22 passed in 1.46s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/test_hotkey_doctor.py tests/analysis/test_remediation.py -q`
  - Result: `30 passed in 1.49s`.
- `uv run pytest`
  - Result: `441 passed in 6.28s`.
- `bash -lc '! rg "provider_audio_basic_scope|basic_provider_audio_placeholder" saymo/analysis tests/analysis tests/test_call_ready_cli.py'`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/provider_audio_readiness.py saymo/analysis/launch_readiness.py saymo/commands/call_ready.py'`
  - Result: passed.
- `rg "provider_meeting_tab|capture_input_device|playback_output_device|provider_output_blackhole|capture_route_blackhole|recording_microphone_input|provider_capabilities|hotkey_accessibility_permission|chrome_automation_permission" tests/analysis/test_provider_audio_readiness.py tests/test_call_ready_cli.py`
  - Result: passed.
- `git diff --check`
  - Result: passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Contract] Split fixed launch order from conditional permission rows**
- **Found during:** Task 2 focused verification.
- **Issue:** The new order test initially required `_LAUNCH_CHECK_ORDER` to include a conditional `hotkey_accessibility_permission` row, but permission rows are emitted only when blockers exist.
- **Fix:** Kept `_LAUNCH_CHECK_ORDER` to the fixed Phase 37 provider/audio sequence and asserted the hotkey permission row follows that sequence only in the dynamic report fixture.
- **Files modified:** `tests/analysis/test_launch_readiness.py`
- **Verification:** Focused, wave, full, and grep validation passed.
- **Committed in:** `af3e37c`

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** No scope expansion; the fix makes the order test match the actual conditional permission contract.

## Issues Encountered

The only verification failure was the test-contract issue documented above. No production blocker, auth gate, or architecture decision occurred.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 37 is complete and ready for Phase 38. The launch gate now exposes provider/audio readiness while keeping mutating provider control, playback, recording, and route changes in explicit diagnostics only.

## Self-Check: PASSED

- Summary file found: `.planning/phases/37-provider-and-audio-remediation/37-04-SUMMARY.md`.
- Task commits found: `663aa95` and `af3e37c`.
- Required RED, selected GREEN, focused, wave, full, grep, and diff-check verification results are recorded above.

---
*Phase: 37-provider-and-audio-remediation*
*Completed: 2026-07-08*
