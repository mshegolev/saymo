---
phase: 36-call-ready-preflight-and-cache-gate
plan: "04"
subsystem: launch-readiness
tags: [saymo, call-ready, remediation, artifacts, pytest, privacy]

requires:
  - phase: 36-02
    provides: daily-note source and prepared-audio launch checks
  - phase: 36-03
    provides: response-cache coverage and cloned-voice launch checks
provides:
  - Full Phase 36 call-ready collector wiring
  - Sanitized launch-readiness JSON artifact writer and CLI output path
  - Grouped block/warn/info remediation for call-ready checks
  - Final Phase 36 validation evidence
affects: [phase-36, phase-37, phase-39, phase-40, call-ready, launch-gate]

tech-stack:
  added: []
  patterns:
    - TDD RED/GREEN commits for call-ready collector, artifacts, and remediation
    - Sanitized JSON artifact output from LaunchReadinessReport.to_dict()
    - Launch-specific remediation hints grouped by check severity

key-files:
  created:
    - .planning/phases/36-call-ready-preflight-and-cache-gate/36-04-SUMMARY.md
  modified:
    - saymo/analysis/launch_readiness.py
    - saymo/analysis/remediation.py
    - saymo/commands/call_ready.py
    - tests/analysis/test_launch_readiness.py
    - tests/test_call_ready_cli.py

key-decisions:
  - "Provider/audio readiness remains an info-only Phase 37 placeholder in Phase 36."
  - "Call-ready artifacts are written from sanitized LaunchReadinessReport.to_dict() JSON and do not mix with JSON stdout."
  - "Grouped remediation uses launch-check labels/actions/rerun commands and severity sections instead of provider/audio deep checks."

patterns-established:
  - "collect_launch_readiness emits daily note, prepared audio, response cache, cloned voice, then provider_audio_basic_scope checks in order."
  - "render_launch_readiness preserves one top-level call-ready status line and appends grouped remediation after check lines."
  - "hints_from_launch_readiness maps launch check keys to source-data, voice-cache, or retest categories."

requirements-completed: [LAUN-01, LAUN-02, LAUN-03, LAUN-04, LAUN-05, LAUN-06, LAUN-07]

duration: 7 min
completed: 2026-07-08
---

# Phase 36 Plan 04: Call-Ready Gate Summary

**Full Phase 36 call-ready gate with sanitized artifacts and grouped remediation over daily-note, prepared-audio, response-cache, and cloned-voice checks.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-08T13:13:25Z
- **Completed:** 2026-07-08T13:20:14Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Wired `collect_launch_readiness` to emit the complete Phase 36 check order: daily-note presence, daily-note source, prepared standup audio, response-cache coverage, cloned-voice metadata, and the Phase 37 provider/audio placeholder.
- Added `write_launch_readiness_artifact()` and `saymo call-ready --output`, with human output printing only `artifact: {path}` and JSON stdout remaining valid JSON.
- Added `hints_from_launch_readiness()` plus grouped `block`, `warn`, and `info` remediation with exact action and rerun commands.
- Ran the focused Phase 36 validation gate and the full repository pytest suite.

## Task Commits

1. **Task 1 RED: Full collector and artifact tests** - `cc242a6` (`test`)
2. **Task 1 GREEN: Full call-ready artifact gate** - `4afe24e` (`feat`)
3. **Task 2 RED: Grouped remediation tests** - `d170689` (`test`)
4. **Task 2 GREEN: Grouped call-ready remediation** - `8c636b9` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/launch_readiness.py` - Full Phase 36 collector, grouped remediation renderer, and sanitized artifact writer.
- `saymo/analysis/remediation.py` - Launch-readiness remediation hint mapping.
- `saymo/commands/call_ready.py` - `--output` path support with privacy-safe artifact output.
- `tests/analysis/test_launch_readiness.py` - Full collector, artifact, and grouped remediation tests.
- `tests/test_call_ready_cli.py` - CLI output/artifact and grouped remediation tests.
- `.planning/phases/36-call-ready-preflight-and-cache-gate/36-04-SUMMARY.md` - Execution evidence and residual scope.

## Decisions Made

- Provider/audio readiness stays as `provider_audio_basic_scope`, `severity="info"`, `ok=True`, detail `deferred_to_phase_37`, and metadata `{"deferred_to_phase": "37", "scope": "basic_provider_audio_placeholder"}`.
- `--output` writes sanitized JSON via `report.to_dict()` and prints the artifact path only in human mode; `--json --output` keeps stdout as pure JSON.
- Remediation grouping is rendered from launch readiness checks, so generated output contains check labels, details, actions, and rerun commands without raw private source text.

## Verification Commands

- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
  - Pre-Task 1 baseline result: `10 passed in 0.18s`
  - Task 1 RED result after adding stricter tests: `4 failed, 10 passed in 0.23s`
  - Task 1 GREEN result: `14 passed in 0.18s`
- `uv run pytest tests/test_call_ready_cli.py::test_call_ready_groups_remediation_with_rerun_commands tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
  - Pre-Task 2 baseline result: `14 passed in 0.18s`
  - Task 2 RED result after adding stricter tests: `2 failed, 13 passed in 0.20s`
  - Task 2 GREEN result: `15 passed in 0.17s`
- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/analysis/test_response_cache.py tests/analysis/test_cache_metadata.py tests/scripts/test_ensure_obsidian_daily_note.py tests/test_trigger_check.py -q`
  - Result: `85 passed in 1.00s`
- `uv run pytest`
  - Result: `433 passed in 4.01s`

## Residual Scope

Phase 37 still owns deep provider tab, Chrome capability, BlackHole route, microphone takeover, and macOS permission readiness. Phase 38 still owns daemon and LaunchAgent readiness. Phase 39 still owns realtime fail-closed gating. Phase 40 still owns scorecard and safety-soak evidence feedback.

## Deviations from Plan

None - implementation scope followed the plan as written.

## Issues Encountered

The plan expected the existing 36-01 RED checks to fail before Task 1 and Task 2 implementation, but the focused suites were already green after Plans 36-02 and 36-03. I preserved TDD by adding stricter Task 1 and Task 2 RED tests, observing the expected failures, committing those tests, and only then writing production code.

## Post-Verification Gap Fix

Initial phase verification found that two remediation actions were not exact:
`daily_note_source_ready` and `prepared_standup_audio` pointed to
`saymo call-ready --prepare`, but that flag only allows missing daily-note
creation and does not add usable note content or synthesize the prepared WAV.

Fix applied:

- `daily_note_source_ready` now tells the user to add usable content to the
  daily note path and then run `saymo prepare -p standup`.
- `prepared_standup_audio` now points to `saymo prepare -p standup`.
- response-cache and voice rerun commands now use `saymo call-ready -p standup
  --provider glip` without the no-op `--prepare`.
- `saymo call-ready` human output uses Rich `soft_wrap=True` so exact action
  commands remain copyable instead of being line-wrapped.

Post-fix verification:

- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
  - Result: `15 passed in 0.16s`
- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/analysis/test_response_cache.py tests/analysis/test_cache_metadata.py tests/scripts/test_ensure_obsidian_daily_note.py tests/test_trigger_check.py -q`
  - Result: `85 passed in 0.77s`
- `uv run pytest`
  - Result: `433 passed in 3.58s`
- `uv run saymo call-ready -p standup --provider glip`
  - Result: exit 1 for current local data, with actionable blockers:
    placeholder daily-note source -> add usable content and run
    `saymo prepare -p standup`; missing prepared WAV -> run
    `saymo prepare -p standup`.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 36 is complete and ready for Phase 37 provider/audio remediation work. The shared launch-readiness contract now exposes sanitized checks, artifacts, and grouped remediation without claiming Phase 37-40 responsibilities.

## Self-Check: PASSED

- Created/modified files found: `saymo/analysis/launch_readiness.py`, `saymo/analysis/remediation.py`, `saymo/commands/call_ready.py`, `tests/analysis/test_launch_readiness.py`, `tests/test_call_ready_cli.py`, and this summary.
- Task commits found: `cc242a6`, `4afe24e`, `d170689`, `8c636b9`.
- Required summary residual scope and focused validation command strings found.

---
*Phase: 36-call-ready-preflight-and-cache-gate*
*Completed: 2026-07-08*
