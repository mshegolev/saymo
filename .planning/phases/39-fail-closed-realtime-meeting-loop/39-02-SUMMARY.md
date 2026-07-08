---
phase: 39-fail-closed-realtime-meeting-loop
plan: "02"
subsystem: realtime-response-policy
tags: [saymo, realtime, response-cache, cloned-voice, fail-closed, pytest]

requires:
  - phase: 39-01
    provides: shared launch-readiness gate before realtime setup
  - phase: 36-03
    provides: response-cache coverage and cloned-voice metadata checks
  - phase: 36-04
    provides: grouped call-ready remediation and sanitized readiness artifacts
provides:
  - Response-cache-only automatic realtime response policy
  - metadata-aware runtime response cache construction
  - fail-closed cache miss, disabled cache, stale metadata, live fallback, and deterministic skip decisions
  - _auto integration that continues listening without playback on non-speak automatic decisions
affects: [phase-39, phase-40, realtime-loop, response-cache, live-control]

tech-stack:
  added: []
  patterns:
    - TDD RED/GREEN commit split for realtime automatic response policy
    - ResponseCache is constructed with build_voice_cache_metadata(config, purpose="response_cache")
    - Automatic realtime policy returns small sanitized decision labels instead of generated fallback content

key-files:
  created:
    - saymo/analysis/realtime_policy.py
    - tests/analysis/test_realtime_policy.py
    - .planning/phases/39-fail-closed-realtime-meeting-loop/39-02-SUMMARY.md
  modified:
    - saymo/commands/core.py
    - tests/test_auto_qa_flow.py

key-decisions:
  - "Automatic realtime answers are response-cache-only: cache hits speak, while cache miss, disabled cache, stale metadata, and live_fallback miss paths block."
  - "Runtime response cache construction uses response-cache cloned-voice metadata, so stale cached WAV sidecars are not playable automatically."
  - "_auto no longer calls the legacy _resolve_auto_response_decision path for automatic playback and does not warm up live-fallback TTS."

patterns-established:
  - "RealtimeResponseDecision carries outcome, label, source, reason, audio path, intent key, confidence, automatic flag, and cleanup flag."
  - "deterministic_should_answer=False returns deterministic-skip before classifier, cache lookup, LLM, or TTS boundaries."
  - "Automatic non-speak decisions reset cooldown and continue listening before pre-speak delay or playback."

requirements-completed: [REAL-03, REAL-06]

duration: 6min
completed: 2026-07-08T17:30:19Z
---

# Phase 39 Plan 02: Fail-Closed Response Policy Summary

**Response-cache-only automatic realtime answers with cloned-voice metadata checks and blocked live fallback paths.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-08T17:24:29Z
- **Completed:** 2026-07-08T17:30:19Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `saymo.analysis.realtime_policy` with `RealtimeResponseDecision`, `build_realtime_response_cache()`, and `resolve_realtime_response_decision()`.
- Built runtime response caches with `build_voice_cache_metadata(config, purpose="response_cache")`, so stale response-cache voice sidecars block automatic playback.
- Replaced `_auto()` automatic response resolution with the new policy and removed realtime TTS warmup for live fallback.
- Added tests for cache hit, intent-classifier cache hit/miss, cache miss, disabled cache, stale metadata, live fallback blocking, deterministic skip, and the `_auto()` legacy resolver guard.

## Task Commits

1. **Task 1 RED: Cache-only automatic policy tests** - `91e7e1d` (`test`)
2. **Task 2 GREEN: Response-cache-only automatic decisions** - `5057982` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/realtime_policy.py` - Fail-closed automatic decision policy and metadata-aware response-cache builder.
- `saymo/commands/core.py` - `_auto()` now uses `build_realtime_response_cache()` and `resolve_realtime_response_decision()` for automatic triggers, skips playback on block/skip, and preserves manual prepared playback.
- `tests/analysis/test_realtime_policy.py` - Unit tests for cache hits, classifier cache routing, blocked fallback paths, stale metadata, disabled cache, and deterministic skip boundaries.
- `tests/test_auto_qa_flow.py` - Regression that `_auto()` does not use the legacy automatic response resolver.
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-02-SUMMARY.md` - Execution evidence and handoff.

## Decisions Made

- Live fallback remains a configured future option but is blocked for automatic realtime cache misses in this plan.
- The policy does not import or call LLM answer generation, TTS engine selection, or synthesis.
- Cached response text and transcript text stay out of `RealtimeResponseDecision`; only stable route labels, intent key, confidence, and audio path are returned.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RED verification failed as expected with `ModuleNotFoundError: No module named 'saymo.analysis.realtime_policy'`; the wrapper command exited 0 because the new tests failed before implementation.
- The required GSD chain-flag clear added `.planning/config.json` noise before task work; it was kept out of task commits and is not part of this plan's implementation.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py -q; test $? -ne 0'`
  - RED result: expected collection failure for missing `saymo.analysis.realtime_policy`; wrapper exited 0.
- `uv run pytest tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py -q`
  - Result: `54 passed in 0.24s`.
- `uv run pytest tests/analysis/test_realtime_gate.py tests/test_call_ready_cli.py -q`
  - Result: `12 passed in 1.33s`.
- `bash -lc '! rg "answer_question\\(|get_selected_tts_engine\\(" saymo/analysis/realtime_policy.py; ! rg "_resolve_auto_response_decision|answer_question\\(" saymo/commands/core.py'`
  - Result: passed.
- `bash -lc '! rg "raw_transcript|generated_answer|answer_text|audio_bytes|PRIVATE_" saymo/analysis/realtime_policy.py'`
  - Result: passed.
- `git diff --check`
  - Result: passed.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 39-03 can add provider-loss, manual-takeover, hard-disable, and disabled-auto-answer blockers around playback. This plan intentionally did not modify provider fallback behavior, manual standup policy, realtime event files, scorecards, or safety-soak.

## Self-Check: PASSED

- Created files found: `saymo/analysis/realtime_policy.py`, `tests/analysis/test_realtime_policy.py`, and this summary.
- Modified files verified: `saymo/commands/core.py` and `tests/test_auto_qa_flow.py`.
- Task commits found: `91e7e1d` and `5057982`.
- Required RED, focused GREEN, launch/call-ready regression, static fail-closed, static privacy, and diff-check validation results are recorded above.

---
*Phase: 39-fail-closed-realtime-meeting-loop*
*Completed: 2026-07-08*
