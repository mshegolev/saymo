---
phase: 37-provider-and-audio-remediation
plan: "01"
subsystem: launch-readiness
tags: [saymo, call-ready, provider-readiness, chrome-tab, pytest, privacy]

requires:
  - phase: 36-call-ready-preflight-and-cache-gate
    provides: shared LaunchReadinessCheck contract, call-ready CLI, JSON artifact path, and grouped remediation
provides:
  - Provider meeting tab readiness check for the shared call-ready gate
  - Non-destructive provider lookup and check_ready-only default behavior
  - Blocking provider errors for unknown providers, missing tabs, factory errors, and check exceptions
  - Focused provider-tab and call-ready CLI regression tests
affects: [phase-37, phase-38, phase-39, call-ready, launch-gate, provider-readiness]

tech-stack:
  added: []
  patterns:
    - Provider/audio checks return LaunchReadinessCheck rows through saymo.analysis.provider_audio_readiness
    - Default provider readiness resolves providers through factory.get_provider and calls only provider.check_ready()
    - Provider error metadata is bounded to sanitized status fields and error_type

key-files:
  created:
    - saymo/analysis/provider_audio_readiness.py
    - tests/analysis/test_provider_audio_readiness.py
    - .planning/phases/37-provider-and-audio-remediation/37-01-SUMMARY.md
  modified:
    - saymo/analysis/launch_readiness.py
    - tests/analysis/test_launch_readiness.py
    - tests/test_call_ready_cli.py

key-decisions:
  - "Provider tab readiness is a blocking LaunchReadinessCheck named provider_meeting_tab."
  - "Default call-ready provider checks call only provider lookup and provider.check_ready(), leaving tab activation, mute, focus, mic switching, playback, recording, config writes, and system route changes out of scope."
  - "Provider factory and check exceptions expose sanitized detail values plus error_type only, not raw exception text."

patterns-established:
  - "collect_provider_audio_checks returns a tuple of launch-readiness checks, with collect_provider_tab_check as the first row."
  - "collect_launch_readiness appends provider/audio checks after cloned voice metadata."
  - "Provider tab metadata includes category, provider_name, configured_provider, url_pattern, meeting_found, app_running, and JSON-safe tab_info."

requirements-completed: [PROV-01, PROV-05]

duration: 5 min
completed: 2026-07-08
---

# Phase 37 Plan 01: Provider Tab Readiness Summary

**Blocking provider meeting tab readiness for call-ready using sanitized, non-destructive Chrome provider checks.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-08T14:04:54Z
- **Completed:** 2026-07-08T14:10:06Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `saymo.analysis.provider_audio_readiness` with `collect_provider_audio_checks()` and `collect_provider_tab_check()`.
- Replaced the Phase 36 `provider_audio_basic_scope` launch collector placeholder with a real `provider_meeting_tab` blocking check.
- Added tests for found tabs, missing tabs, unknown providers, provider factory errors, provider check exceptions, CLI JSON/human output, and default non-destructive provider behavior.

## Task Commits

1. **Task 1 RED: Provider-tab readiness contracts** - `906dda8` (`test`)
2. **Task 2 GREEN: Provider meeting tab readiness** - `1d48c95` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/provider_audio_readiness.py` - Provider/audio launch-readiness helper with provider tab checks.
- `saymo/analysis/launch_readiness.py` - Launch collector wiring from cloned voice metadata to provider/audio checks.
- `tests/analysis/test_provider_audio_readiness.py` - Provider tab and non-destructive behavior tests.
- `tests/analysis/test_launch_readiness.py` - Collector order and remediation fixture updates for `provider_meeting_tab`.
- `tests/test_call_ready_cli.py` - CLI JSON and human output expectation for `provider_meeting_tab`.
- `.planning/phases/37-provider-and-audio-remediation/37-01-SUMMARY.md` - Execution summary.

## Decisions Made

- Provider tab readiness uses `severity="block"` whether passing or failing, so a missing provider tab blocks launch readiness.
- Unknown providers use detail `unknown_provider`; other provider factory or `check_ready()` exceptions use detail `provider_check_error`.
- Error metadata intentionally records only `error_type`, avoiding raw exception text in sanitized JSON or artifacts.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_provider_audio_readiness.py::test_provider_tab_readiness_reports_found_missing_and_errors tests/test_call_ready_cli.py::test_call_ready_includes_provider_tab_readiness -q; test $? -ne 0'`
  - RED result: command exited 0 after expected failures, `2 failed in 0.22s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_provider_tab_readiness_reports_found_missing_and_errors tests/test_call_ready_cli.py::test_call_ready_includes_provider_tab_readiness tests/analysis/test_launch_readiness.py::test_collect_launch_readiness_wires_full_phase36_order -q`
  - Result: `3 passed in 0.18s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_provider_tab_readiness_reports_found_missing_and_errors tests/analysis/test_provider_audio_readiness.py::test_collect_provider_audio_checks_is_non_destructive tests/test_call_ready_cli.py::test_call_ready_includes_provider_tab_readiness tests/analysis/test_launch_readiness.py -q`
  - Result: `12 passed in 0.50s`.
- `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
  - Final focused result: `18 passed in 0.78s`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The first Task 2 acceptance grep caught one leftover placeholder fixture in `tests/analysis/test_launch_readiness.py`. It was part of a remediation-rendering test, not production collector output. I updated that fixture to use `provider_meeting_tab` before committing Task 2.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 37-02. The call-ready collector now has a real provider tab row that later BlackHole route, microphone takeover, capability, and permission checks can extend through `collect_provider_audio_checks()`.

## Self-Check: PASSED

- Created/modified files found: `saymo/analysis/provider_audio_readiness.py`, `tests/analysis/test_provider_audio_readiness.py`, `saymo/analysis/launch_readiness.py`, `tests/analysis/test_launch_readiness.py`, `tests/test_call_ready_cli.py`, and this summary.
- Task commits found: `906dda8` and `1d48c95`.
- Required focused verification results are recorded above.

---
*Phase: 37-provider-and-audio-remediation*
*Completed: 2026-07-08*
