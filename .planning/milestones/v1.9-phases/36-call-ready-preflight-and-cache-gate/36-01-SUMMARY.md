---
phase: 36-call-ready-preflight-and-cache-gate
plan: "01"
subsystem: launch-readiness
tags: [saymo, click, pytest, call-ready, launch-readiness, privacy]

requires:
  - phase: 34-call-ready-engine-selector-and-fallback-chain
    provides: privacy-safe voice selector and cache metadata foundations
  - phase: 35-preview-a-b-approval-and-safety-soak
    provides: approved cloned-voice readiness context
provides:
  - Shared LaunchReadinessCheck and LaunchReadinessReport contracts
  - Thin saymo call-ready CLI shell with human and JSON output
  - Phase 36 RED tests for daily-note, prepared-audio, response-cache, voice metadata, and remediation follow-up plans
affects: [phase-36, phase-37, phase-39, phase-40, call-ready, launch-gate]

tech-stack:
  added: []
  patterns:
    - Frozen dataclasses for launch-readiness reports
    - Thin Click command wrapper delegating to analysis contracts
    - Privacy-safe serialization and human rendering

key-files:
  created:
    - saymo/analysis/launch_readiness.py
    - saymo/commands/call_ready.py
    - tests/analysis/test_launch_readiness.py
    - tests/test_call_ready_cli.py
  modified:
    - saymo/commands/__init__.py
    - tests/analysis/test_response_cache.py
    - tests/analysis/test_cache_metadata.py

key-decisions:
  - "Phase 36.01 collector intentionally emits only contract-safe profile and provider scope checks; deeper provider, audio, daily-note, cache, and voice checks remain deferred."
  - "Human call-ready output has exactly one top-level status line; JSON uses LaunchReadinessReport.to_dict()."
  - "Sanitization redacts known private fixture sentinels and token/secret-like values before rendering or serializing."

patterns-established:
  - "LaunchReadinessCheck carries key, label, severity, ok, detail, action, rerun, and metadata for future phases."
  - "LaunchReadinessReport.ready is false only when a blocking check fails."
  - "Command modules stay thin and are registered by the bottom import in saymo/commands/__init__.py."

requirements-completed: [LAUN-01, LAUN-07]

duration: 6 min
completed: 2026-07-08
---

# Phase 36 Plan 01: Shared Launch-Readiness Contracts Summary

**Privacy-safe launch-readiness contracts and a registered `saymo call-ready` command shell with executable RED tests for the remaining Phase 36 checks.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-08T12:51:17Z
- **Completed:** 2026-07-08T12:57:58Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added `LaunchReadinessCheck`, `LaunchReadinessReport`, `collect_launch_readiness`, and `render_launch_readiness`.
- Added `saymo call-ready -p standup --provider glip` with one top-level human status line, JSON mode, provider resolution, and exit code based on blocking checks.
- Seeded Phase 36 RED tests for later daily-note, prepared-audio, response-cache, cloned-voice metadata, `--prepare`, and grouped remediation work.

## Task Commits

1. **Task 0 RED tests:** `c553b84` (`test`) - added launch readiness, CLI, response-cache, and metadata RED tests.
2. **Task 0 test-spec fix:** `5bc73e1` (`test`) - tightened `--prepare` future test to require missing daily-note creation.
3. **Task 1 GREEN implementation:** `215813d` (`feat`) - added contracts, command wrapper, and CLI registration.

_Note: TDD produced test commits before the feature commit._

## Files Created/Modified

- `saymo/analysis/launch_readiness.py` - shared readiness dataclasses, collector shell, sanitized serialization, and human renderer.
- `saymo/commands/call_ready.py` - Click command wrapper for human and JSON output.
- `saymo/commands/__init__.py` - imports `call_ready` so decorators register the command.
- `tests/analysis/test_launch_readiness.py` - report contract tests plus future Phase 36 RED checks.
- `tests/test_call_ready_cli.py` - CLI status, JSON, `--prepare`, and grouped remediation tests.
- `tests/analysis/test_response_cache.py` - future RED response-cache coverage test.
- `tests/analysis/test_cache_metadata.py` - future RED source digest metadata test.

## Decisions Made

- Kept the initial collector scoped to profile and `provider_basic_scope` info rows with `deferred_to_phase=37`; it does not claim provider/audio readiness.
- Used one top-level human line, `call-ready: ready` or `call-ready: not ready`, with grouped severity details below it.
- Kept output privacy-safe by serializing sanitized fields only; tests verify sentinel strings are absent.

## Verification Commands

- `uv run pytest tests/analysis/test_launch_readiness.py::test_report_ready_false_when_blocking_check_fails tests/test_call_ready_cli.py::test_call_ready_prints_top_level_result -q` - RED before implementation: 2 failed as expected, missing `saymo.analysis.launch_readiness` and `saymo.commands.call_ready`.
- `uv run pytest tests/analysis/test_launch_readiness.py::test_report_ready_false_when_blocking_check_fails tests/analysis/test_launch_readiness.py::test_report_serializes_without_private_text tests/test_call_ready_cli.py::test_call_ready_prints_top_level_result tests/test_call_ready_cli.py::test_call_ready_json_is_sanitized -q` - PASS, 4 passed.
- `uv run saymo call-ready -p standup --provider glip` - PASS, exit 0, one top-level `call-ready: ready` line, provider row marked `deferred_to_phase=37`.
- `uv run saymo call-ready -p standup --provider glip --json` - PASS, valid sanitized JSON with `ready`, `profile`, `provider`, and `checks`.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q` - EXPECTED FUTURE RED, 4 failed and 5 passed; failures are missing daily-note, prepared-audio, cloned-voice, and missing-note creation behavior for plans 36-02 through 36-04.
- `uv run pytest tests/analysis/test_response_cache.py::test_response_cache_coverage_reports_missing_and_stale_variants tests/analysis/test_cache_metadata.py::test_voice_cache_metadata_records_source_digest_without_text -q` - EXPECTED FUTURE RED, 2 failed; failures are missing `response_cache_coverage` and `source_sha256`.
- `uv run pytest tests/scripts/test_ensure_obsidian_daily_note.py -q` - PASS, 3 passed.
- `uv run pytest tests/test_trigger_check.py tests/test_rehearsal_cli.py -q` - PASS, 52 passed.
- `uv run pytest tests/analysis/test_cache_metadata.py::test_voice_cache_metadata_writes_privacy_safe_sidecar tests/analysis/test_cache_metadata.py::test_voice_cache_metadata_check_rejects_missing_and_stale_sidecars tests/analysis/test_response_cache.py::test_build_regenerates_when_voice_metadata_is_stale -q` - PASS, 3 passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tightened future `--prepare` RED test**
- **Found during:** Task 1 verification
- **Issue:** The seeded `test_call_ready_prepare_creates_note_without_overwrite` preserved existing note content but did not prove missing note creation.
- **Fix:** Added a second invocation after deleting the note, asserting `--prepare` creates it with the standup template.
- **Files modified:** `tests/test_call_ready_cli.py`
- **Verification:** `uv run pytest tests/test_call_ready_cli.py::test_call_ready_prepare_creates_note_without_overwrite -q` now fails for the planned future behavior.
- **Committed in:** `5bc73e1`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix strengthened the intended RED test without expanding production scope.

## Issues Encountered

Expected future RED tests remain for later Phase 36 plans:

- `daily_note_source`, `prepared_audio`, and `cloned_voice` checks are not collected yet.
- `call-ready --prepare` does not create a missing daily note yet.
- `response_cache_coverage` and metadata `source_sha256` are not implemented yet.

These are deliberate follow-up gates for plans 36-02 through 36-04, not blockers for 36-01.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for 36-02 to add daily-note source and prepared standup audio checks on top of the shared `LaunchReadinessReport` contract.

## Self-Check: PASSED

- Created files found: `saymo/analysis/launch_readiness.py`, `saymo/commands/call_ready.py`, `tests/analysis/test_launch_readiness.py`, `tests/test_call_ready_cli.py`, and this summary.
- Task commits found: `c553b84`, `5bc73e1`, `215813d`.

---
*Phase: 36-call-ready-preflight-and-cache-gate*
*Completed: 2026-07-08*
