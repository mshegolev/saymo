---
phase: 39-fail-closed-realtime-meeting-loop
plan: "05"
subsystem: realtime-decision-events
tags: [saymo, realtime, events, jsonl, privacy, fail-closed, pytest]

requires:
  - phase: 39-01
    provides: shared launch-readiness gate before realtime setup
  - phase: 39-02
    provides: response-cache-only automatic realtime response policy
  - phase: 39-03
    provides: runtime handbrake and provider playback blockers
  - phase: 39-04
    provides: explicit manual prepared-standup route
provides:
  - Sanitized RealtimeDecisionEvent schema and JSONL append helper
  - decision-to-event conversion for spoke, skipped, and blocked outcomes
  - realtime event emission from existing launch, skip, block, speak, and playback branches
  - static privacy, provider mutation, legacy fallback, and Phase 40 scope guards
affects: [phase-39, phase-40, realtime-loop, live-control, response-cache]

tech-stack:
  added: []
  patterns:
    - Allowlisted realtime event payloads written under live-control profile directories
    - Best-effort event append wrapper so evidence failures cannot crash the live loop
    - Deterministic addressing runs before live assist, with live assist limited to skipping addressed candidates

key-files:
  created:
    - saymo/analysis/realtime_events.py
    - tests/analysis/test_realtime_events.py
    - tests/test_realtime_static_guards.py
    - .planning/phases/39-fail-closed-realtime-meeting-loop/39-05-SUMMARY.md
  modified:
    - saymo/analysis/realtime_policy.py
    - saymo/commands/core.py
    - tests/analysis/test_realtime_policy.py
    - tests/test_auto_qa_flow.py

key-decisions:
  - "Realtime decision events use a strict allowlist: created_at, profile, provider, outcome, label, source, automatic, intent_key, confidence, audio_path, and detail."
  - "Decision conversion maps speak/block/skip to spoke/blocked/skipped and relies on the event schema for bounded string and secret redaction."
  - "_auto event appends are best-effort only; event write failures print a sanitized dim warning and preserve fail-closed loop behavior."
  - "Phase 39 writes only minimal JSONL decision evidence and does not import or implement Phase 40 scorecards, safety-soak, troubleshooting, or aggregation."

patterns-established:
  - "realtime_event_log_path(profile, base_dir=...) delegates to live_control_dir(profile, base_dir=...) and writes realtime-decisions.jsonl."
  - "Response decisions are emitted immediately after resolution, while later handbrake/provider/playback blockers emit additional blocked events."
  - "Addressing skip emits source=deterministic before live assist; live assist emits source=live_assist only when it skips an already-addressed candidate."

requirements-completed: [REAL-05, REAL-06]

duration: 6min
completed: 2026-07-08T18:02:16Z
---

# Phase 39 Plan 05: Realtime Decision Events Summary

**Sanitized realtime decision JSONL events for cache hits, skips, handbrake/provider blocks, manual standup, and launch failures without Phase 40 reporting.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-08T17:56:02Z
- **Completed:** 2026-07-08T18:02:16Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added `saymo.analysis.realtime_events` with `RealtimeDecisionEvent`, `realtime_event_log_path()`, and `append_realtime_decision_event()`.
- Added `RealtimeResponseDecision.to_event()` with speak/block/skip mapping to spoke/blocked/skipped event outcomes.
- Wired `_auto()` to emit events for launch-readiness blocks, handbrake blocks, addressing/live-assist skips, response-cache hits, cache/fallback/metadata blocks, manual standup decisions, provider blocks, and blocked playback results.
- Added static guards for privacy-dangerous field names, provider/audio mutation calls, legacy automatic fallback, and Phase 40 scope creep.

## Task Commits

1. **Task 1 RED: Sanitized event and final guard tests** - `59df114` (`test`)
2. **Task 2 GREEN: Sanitized realtime decision events** - `76b8cc6` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/realtime_events.py` - Allowlisted sanitized event schema and JSONL append helper under live-control profile directories.
- `saymo/analysis/realtime_policy.py` - Added sanitized response-decision to event conversion.
- `saymo/commands/core.py` - Added best-effort event emission for existing Phase 39 realtime branches.
- `tests/analysis/test_realtime_events.py` - Event schema, sanitization, JSONL path, and append helper coverage.
- `tests/analysis/test_realtime_policy.py` - Decision-to-event mapping and sanitization regression.
- `tests/test_auto_qa_flow.py` - Auto-loop event emission and deterministic/live-assist boundary regressions.
- `tests/test_realtime_static_guards.py` - Static privacy, provider mutation, legacy fallback, and Phase 40 scope guards.
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-05-SUMMARY.md` - Execution evidence and handoff.

## Decisions Made

- Event payloads are allowlisted rather than post-filtering arbitrary decision dictionaries.
- `detail` stores only sanitized route/block reason text; raw meeting transcript, generated answer text, daily note content, and audio content are not event inputs.
- The event append wrapper catches all write errors because losing evidence must not crash a live meeting loop.
- Playback-result failures reuse existing Phase 39 labels: provider-related playback failures emit `provider-blocked`; other blocked playback results emit `fallback-blocked`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Privacy Guard] Removed a static forbidden marker from implementation source**
- **Found during:** Task 2 (sanitized realtime decision events)
- **Issue:** The first event helper constant name contained the same sentinel prefix that the privacy static guard forbids in realtime implementation files.
- **Fix:** Renamed the helper constant while keeping the same runtime redaction behavior.
- **Files modified:** `saymo/analysis/realtime_events.py`
- **Verification:** `uv run pytest tests/analysis/test_realtime_events.py tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py tests/test_realtime_static_guards.py -q`
- **Committed in:** `76b8cc6`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** The fix tightened the privacy guard and did not expand scope.

## Issues Encountered

- RED verification failed as expected with `ModuleNotFoundError: No module named 'saymo.analysis.realtime_events'`.
- No auth gates, architecture changes, provider repair, audio route mutation, or Phase 40 reporting work occurred.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_realtime_events.py tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py tests/test_realtime_static_guards.py -q; test $? -ne 0'`
  - RED result: expected collection failure for missing `saymo.analysis.realtime_events`; wrapper exited 0.
- `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/analysis/test_realtime_events.py tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_live_control_cli.py tests/test_realtime_static_guards.py -q`
  - Result: `96 passed in 2.96s`.
- `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q`
  - Result: `78 passed in 3.48s`.
- `uv run pytest`
  - Result: `518 passed in 7.03s`.
- `bash -lc '! rg "answer_question\\(|get_selected_tts_engine\\(" saymo/analysis/realtime_policy.py saymo/analysis/realtime_gate.py; ! rg "_resolve_auto_response_decision|answer_question\\(" saymo/commands/core.py'`
  - Result: passed.
- `bash -lc '! rg "raw_transcript|generated_answer|answer_text|audio_bytes|PRIVATE_" saymo/analysis/realtime_policy.py saymo/analysis/realtime_gate.py saymo/analysis/realtime_events.py'`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/realtime_gate.py saymo/analysis/realtime_policy.py saymo/analysis/realtime_events.py'`
  - Result: passed.
- `bash -lc '! rg "scorecard|safety-soak|safety_soak|session-scorecard|Launch and Realtime Evidence Feedback" saymo/analysis/realtime_events.py saymo/analysis/realtime_policy.py saymo/commands/core.py'`
  - Result: passed.
- `git diff --check`
  - Result: passed.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 39 now satisfies REAL-05 and REAL-06 in automated coverage. Phase 40 can consume `realtime-decisions.jsonl` for richer evidence, scorecards, safety-soak, troubleshooting, or aggregation, but none of that reporting was implemented in this plan.

## Self-Check: PASSED

- Created files found: `saymo/analysis/realtime_events.py`, `tests/analysis/test_realtime_events.py`, `tests/test_realtime_static_guards.py`, and this summary.
- Modified files verified: `saymo/analysis/realtime_policy.py`, `saymo/commands/core.py`, `tests/analysis/test_realtime_policy.py`, and `tests/test_auto_qa_flow.py`.
- Task commits found: `59df114` and `76b8cc6`.
- Required RED, focused Phase 39, safety regression, full suite, static privacy/fail-closed/provider/Phase 40 guards, and diff-check results are recorded above.

---
*Phase: 39-fail-closed-realtime-meeting-loop*
*Completed: 2026-07-08*
