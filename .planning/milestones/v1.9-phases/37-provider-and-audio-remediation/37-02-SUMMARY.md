---
phase: 37-provider-and-audio-remediation
plan: "02"
subsystem: launch-readiness
tags: [saymo, call-ready, audio-routing, blackhole, pytest, privacy]

requires:
  - phase: 36-call-ready-preflight-and-cache-gate
    provides: shared LaunchReadinessCheck contract, call-ready CLI, JSON artifact path, and grouped remediation
  - phase: 37-provider-and-audio-remediation
    plan: "01"
    provides: provider meeting tab readiness helper and non-destructive provider check pattern
provides:
  - Read-only audio route readiness checks for configured capture, playback, BlackHole, and recording microphone devices
  - Blocking audio-device launch checks with exact device names, kinds, required/found metadata, and bounded device metadata
  - Regression coverage proving provider/audio readiness avoids route mutation, playback, recording, mic switching, and config writes
affects: [phase-37, phase-38, phase-39, call-ready, launch-gate, audio-routing]

tech-stack:
  added: []
  patterns:
    - Audio route readiness uses saymo.audio.devices.find_device with explicit input/output kinds
    - collect_provider_audio_checks returns provider tab readiness followed by route visibility checks
    - Missing required audio devices block launch readiness with non-mutating remediation commands

key-files:
  created:
    - .planning/phases/37-provider-and-audio-remediation/37-02-SUMMARY.md
  modified:
    - saymo/analysis/provider_audio_readiness.py
    - tests/analysis/test_provider_audio_readiness.py
    - tests/test_call_ready_cli.py

key-decisions:
  - "Call-ready audio route checks validate device visibility only; system route changes, playback, recording, and mic switching stay out of the default launch gate."
  - "BlackHole 2ch is validated as an output device for provider audio injection, while BlackHole 16ch and recording_device are validated as input devices."
  - "All five audio route rows use severity=block, so missing required devices prevent call-ready from reporting ready."

patterns-established:
  - "Audio route metadata includes category, device_name, kind, required, found, and a bounded device object only when a device is found."
  - "Tests monkeypatch saymo.audio.devices.find_device instead of touching real sounddevice state."

requirements-completed: [PROV-02, PROV-05]

duration: 4 min
completed: 2026-07-08
---

# Phase 37 Plan 02: Audio Route Readiness Summary

**Read-only BlackHole and microphone route checks now block call-ready when required audio devices are not visible.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-08T14:16:22Z
- **Completed:** 2026-07-08T14:20:22Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `collect_audio_route_checks(config, *, profile, provider_name)` under `saymo.analysis.provider_audio_readiness`.
- Extended `collect_provider_audio_checks()` so `provider_meeting_tab` is followed by `capture_input_device`, `playback_output_device`, `provider_output_blackhole`, `capture_route_blackhole`, and `recording_microphone_input`.
- Added TDD coverage for exact device/kind lookups, blocking missing-device metadata, and non-destructive provider/audio behavior.

## Task Commits

1. **Task 1 RED: Audio-route readiness tests** - `5548c61` (`test`)
2. **Task 2 GREEN: Read-only audio-route checks** - `1ce4e8c` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/provider_audio_readiness.py` - Adds read-only audio route checks and appends them to provider/audio launch readiness.
- `tests/analysis/test_provider_audio_readiness.py` - Adds route/kind, metadata, action, rerun, and non-destructive regression tests.
- `tests/test_call_ready_cli.py` - Updates the provider-tab CLI fixture so new required audio rows are visible in that scenario.
- `.planning/phases/37-provider-and-audio-remediation/37-02-SUMMARY.md` - Execution summary.

## Decisions Made

- Missing audio devices use `detail="device_not_found"` and passing devices use `detail="device_found"`.
- Found device metadata is bounded to `index`, `name`, channel counts, and `default_samplerate`.
- The helper deliberately avoids importing playback, recording, macOS audio mutation, provider mic-switching, or config-writing helpers.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_provider_audio_readiness.py::test_audio_route_checks_validate_expected_devices_and_kinds -q; test $? -ne 0'`
  - RED result: command exited 0 after the expected failure, `1 failed in 0.18s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_audio_route_checks_validate_expected_devices_and_kinds tests/analysis/test_provider_audio_readiness.py::test_collect_provider_audio_checks_is_non_destructive -q`
  - Result: `2 passed in 0.27s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
  - Result: `19 passed in 0.91s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/test_hotkey_doctor.py tests/analysis/test_remediation.py -q`
  - Result: `26 passed in 1.04s`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Fixture] Updated provider-tab CLI fixture for required audio rows**
- **Found during:** Task 2 phase-focused verification
- **Issue:** `test_call_ready_includes_provider_tab_readiness` still modeled only provider-tab readiness. After adding required audio rows, the fixture had no configured recording mic and did not mock visible audio devices, so call-ready correctly returned not ready.
- **Fix:** Added test audio config and a monkeypatched `saymo.audio.devices.find_device` in that fixture.
- **Files modified:** `tests/test_call_ready_cli.py`
- **Verification:** `uv run pytest tests/test_call_ready_cli.py::test_call_ready_includes_provider_tab_readiness -q` and the full phase-focused suite passed.
- **Committed in:** `1ce4e8c`

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** No scope expansion; the fix keeps existing CLI coverage aligned with the new required audio-device gate.

## Issues Encountered

The initial phase-focused run failed only in the CLI fixture described above. Production code did not require a second design pass.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 37-03 can build provider capability rows on top of the same non-destructive `collect_provider_audio_checks()` extension point. The audio route rows now provide stable metadata and blocking semantics for later realtime launch gating.

## Self-Check: PASSED

- Created/modified files found: `saymo/analysis/provider_audio_readiness.py`, `tests/analysis/test_provider_audio_readiness.py`, `tests/test_call_ready_cli.py`, and this summary.
- Task commits found: `5548c61` and `1ce4e8c`.
- Required focused and wave verification results are recorded above.

---
*Phase: 37-provider-and-audio-remediation*
*Completed: 2026-07-08*
