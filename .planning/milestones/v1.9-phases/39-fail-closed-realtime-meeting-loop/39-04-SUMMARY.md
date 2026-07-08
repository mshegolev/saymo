---
phase: 39-fail-closed-realtime-meeting-loop
plan: "04"
subsystem: realtime-manual-standup-playback
tags: [saymo, realtime, manual-speak, response-cache, fail-closed, pytest]

requires:
  - phase: 39-02
    provides: response-cache-only automatic realtime response policy
  - phase: 39-03
    provides: runtime handbrake/provider playback blockers and strict automatic provider fallback
provides:
  - Explicit manual prepared-standup decision helper
  - force-speak route separated from automatic cache-miss handling
  - manual hotkey regression coverage for takeover, hard-disable, already-speaking, and auto-answer-off states
  - automatic cache-miss regression proving no prepared standup path is returned
affects: [phase-39, phase-40, realtime-loop, manual-speak, response-cache]

tech-stack:
  added: []
  patterns:
    - TDD RED/GREEN commit split for manual standup route separation
    - Manual prepared playback uses RealtimeResponseDecision with automatic=false and source=manual_standup
    - Automatic realtime response decisions remain cache-only and never receive a prepared standup fallback path

key-files:
  created:
    - .planning/phases/39-fail-closed-realtime-meeting-loop/39-04-SUMMARY.md
  modified:
    - saymo/analysis/realtime_policy.py
    - saymo/commands/core.py
    - tests/analysis/test_realtime_policy.py
    - tests/test_auto_qa_flow.py

key-decisions:
  - "Explicit manual prepared playback is a separate manual_standup route labeled manual-standup-requested, not a response-cache fallback."
  - "Manual standup blocks use label manual-standup-blocked with stable sanitized reasons such as prepared-standup-missing and manual-takeover."
  - "Manual provider fallback remains enabled through automatic=false, while automatic cached playback remains strict."

patterns-established:
  - "resolve_manual_standup_decision() is the only policy helper used by _auto() force-speak for prepared standup playback."
  - "_request_manual_speak() continues to reject manual takeover, hard-disable, and already-speaking states, while auto-answer-off is not part of the manual rejection boundary."

requirements-completed: [REAL-04]

duration: 4min
completed: 2026-07-08T17:50:37Z
---

# Phase 39 Plan 04: Manual Standup Route Summary

**Explicit prepared-standup playback now has its own manual decision route, while automatic cache misses stay blocked.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-08T17:46:33Z
- **Completed:** 2026-07-08T17:50:37Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `resolve_manual_standup_decision()` with speak/block outcomes for explicit prepared standup playback.
- Replaced `_auto()` force-speak's inline decision with the manual helper and preserved provider fallback for manual playback only.
- Added tests proving manual success/block labels, automatic cache-miss separation, and manual hotkey behavior around handbrake states.

## Task Commits

1. **Task 1 RED: Manual standup separation tests** - `b37cc77` (`test`)
2. **Task 2 GREEN: Explicit manual standup playback route** - `595bddf` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/realtime_policy.py` - Added `resolve_manual_standup_decision()` for explicit prepared standup decisions.
- `saymo/commands/core.py` - Routed force-speak through the manual helper and kept fallback enabled only for manual decisions.
- `tests/analysis/test_realtime_policy.py` - Covered manual speak/block decisions and automatic cache-miss separation.
- `tests/test_auto_qa_flow.py` - Covered manual speak queueing and force-speak bypass of automatic cache/classifier/LLM/TTS paths.
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-04-SUMMARY.md` - Execution evidence and handoff.

## Decisions Made

- Manual prepared standup playback uses `source="manual_standup"` and `automatic=False`.
- Missing prepared standup audio blocks with reason `prepared-standup-missing` and never returns the path.
- A supplied runtime handbrake block maps to `manual-standup-blocked` while preserving only the stable block reason.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RED verification failed as expected with missing `resolve_manual_standup_decision()` and the existing direct force-speak decision not calling the helper.
- No auth gates, architecture changes, or out-of-scope fixes occurred.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py -q; test $? -ne 0'`
  - RED result: expected 4 failures for missing manual helper and direct force-speak decision; wrapper exited 0.
- `uv run pytest tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py -q`
  - Result: `65 passed in 1.80s`.
- `uv run pytest tests/analysis/test_realtime_gate.py tests/test_call_ready_cli.py tests/test_live_control_cli.py -q`
  - Result: `18 passed in 1.20s`.
- `bash -lc '! rg "manual-standup-requested" saymo/analysis/realtime_policy.py saymo/commands/core.py | rg "cache-miss"'`
  - Result: passed.
- `git diff --check`
  - Result: passed.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 39-05 can continue with realtime evidence or remaining Phase 39 validation work. This plan intentionally did not change launch startup gating, provider readiness helpers, event JSONL output, scorecards, safety-soak, provider repair, audio route mutation, or Phase 40 work.

## Self-Check: PASSED

- Created summary found: `.planning/phases/39-fail-closed-realtime-meeting-loop/39-04-SUMMARY.md`.
- Modified files found: `saymo/analysis/realtime_policy.py`, `saymo/commands/core.py`, `tests/analysis/test_realtime_policy.py`, and `tests/test_auto_qa_flow.py`.
- Task commits found: `b37cc77` and `595bddf`.
- Required RED, focused GREEN, runtime/call-ready/live-control regression, static manual/cache-miss separation, and diff-check results are recorded above.

---
*Phase: 39-fail-closed-realtime-meeting-loop*
*Completed: 2026-07-08*
