---
phase: 39-fail-closed-realtime-meeting-loop
plan: "03"
subsystem: realtime-runtime-playback-gates
tags: [saymo, realtime, provider-readiness, handbrake, fail-closed, pytest]

requires:
  - phase: 39-01
    provides: shared launch-readiness gate before realtime setup
  - phase: 39-02
    provides: response-cache-only automatic realtime response policy
provides:
  - Runtime handbrake blockers for auto-answer off, manual takeover, and hard-disable
  - Runtime provider readiness blocker immediately before automatic playback
  - Strict automatic cached-playback mode that does not fall back to direct BlackHole playback
  - RED/GREEN regression coverage for provider drift, provider automation failure, and handbrake state changes
affects: [phase-39, phase-40, realtime-loop, live-control, provider-playback]

tech-stack:
  added: []
  patterns:
    - TDD RED/GREEN commit split for runtime playback blockers
    - RealtimePlaybackBlock carries stable label/reason/detail strings without raw transcript or provider exception text
    - Automatic realtime playback passes allow_provider_fallback=false while manual/non-automatic callers keep the default

key-files:
  created:
    - .planning/phases/39-fail-closed-realtime-meeting-loop/39-03-SUMMARY.md
  modified:
    - saymo/analysis/realtime_gate.py
    - saymo/commands/__init__.py
    - saymo/commands/core.py
    - tests/analysis/test_realtime_gate.py
    - tests/test_auto_qa_flow.py

key-decisions:
  - "Automatic runtime blocks use stable labels: handbrake-blocked and provider-blocked."
  - "Provider drift is checked with the existing provider object via provider.check_ready() immediately before automatic playback."
  - "Provider automation fallback is opt-in strict for automatic realtime only; manual and existing non-automatic playback callers retain default fallback behavior."

patterns-established:
  - "automatic_handbrake_block() is the shared runtime handbrake decision for automatic answers before resolution and before playback."
  - "provider_playback_block() performs a non-mutating pre-play provider readiness check and sanitizes readiness exceptions to exception type only."
  - "_trigger_loop() resets cooldown and continues listening on handbrake/provider blocks without calling _play_cached_audio()."

requirements-completed: [REAL-03]

duration: 5min
completed: 2026-07-08T17:41:11Z
---

# Phase 39 Plan 03: Runtime Playback Blockers Summary

**Automatic realtime playback now fails closed on volatile handbrake and provider state before audio can start.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-08T17:36:01Z
- **Completed:** 2026-07-08T17:41:11Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `RealtimePlaybackBlock`, `automatic_handbrake_block()`, and `provider_playback_block()` in `saymo.analysis.realtime_gate`.
- Wired `_trigger_loop()` to block automatic answers before response resolution and again immediately before playback when auto-answer is off, manual takeover is active, or hard-disable is active.
- Added an immediate provider readiness check before automatic playback; provider loss blocks without calling `_play_cached_audio()`.
- Added `allow_provider_fallback` to `_play_cached_audio()` and passed `False` for automatic realtime playback so provider automation failure before playback cannot fall back to direct BlackHole playback.
- Preserved Plan 39-02 cache-only automatic policy and default fallback behavior for explicit non-automatic playback callers.

## Task Commits

1. **Task 1 RED: Runtime playback blocker tests** - `1068d78` (`test`)
2. **Task 2 GREEN: Runtime provider and handbrake blockers** - `69fef32` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/realtime_gate.py` - Runtime playback block dataclass plus handbrake/provider block helpers.
- `saymo/commands/__init__.py` - Strict cached playback option that blocks direct fallback when provider automation fails before playback starts.
- `saymo/commands/core.py` - `_trigger_loop()` integration before response resolution, after pre-speak delay, and before automatic playback.
- `tests/analysis/test_realtime_gate.py` - Unit coverage for stable handbrake/provider block labels and sanitized provider exceptions.
- `tests/test_auto_qa_flow.py` - Automatic loop regressions for handbrake blocks, provider drift before playback, strict fallback, and default non-automatic fallback.

## Decisions Made

- Provider pre-play checks reuse the provider object created during startup and call only `check_ready()`.
- Provider-block audit evidence uses existing live-control action `status` with result `provider-blocked`, avoiding a new live-control action protocol in this plan.
- Manual `force_speak` playback keeps provider fallback enabled; strict fallback is limited to automatic realtime playback.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reused an existing live-control audit action for provider blocks**
- **Found during:** Task 2 (runtime provider and handbrake blockers)
- **Issue:** Initial provider-block audit used action `provider_check`, which live-control audit normalization rejects as an unknown action.
- **Fix:** Kept result `provider-blocked` but changed the action to existing `status`.
- **Files modified:** `saymo/commands/core.py`
- **Verification:** `uv run pytest tests/analysis/test_realtime_gate.py tests/test_auto_qa_flow.py -q`
- **Committed in:** `69fef32`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** The fix kept provider-block evidence sanitized and avoided introducing a new live-control protocol action outside the plan scope.

## Issues Encountered

- RED verification failed as expected with `ImportError` for missing `automatic_handbrake_block`.
- The GREEN test harness needed its fake `live_control_dir()` to accept the real `base_dir` keyword while exercising provider-block audit output.
- GSD state/roadmap update commands advanced the data but left rendered table/text formatting inconsistent; the metadata text was corrected before the docs commit.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_realtime_gate.py tests/test_auto_qa_flow.py -q; test $? -ne 0'`
  - RED result: expected import failure for missing `automatic_handbrake_block`; wrapper exited 0.
- `uv run pytest tests/analysis/test_realtime_gate.py tests/test_auto_qa_flow.py -q`
  - Result: `59 passed in 1.58s`.
- `uv run pytest tests/analysis/test_realtime_policy.py tests/test_call_ready_cli.py tests/test_live_control_cli.py -q`
  - Result: `19 passed in 1.23s`.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/realtime_gate.py'`
  - Result: passed.
- `git diff --check`
  - Result: passed.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 39-04 can now scope explicit manual prepared-standup policy separately. This plan intentionally did not add event JSONL, provider repair, audio route mutation, Chrome destructive actions, manual standup policy, or Phase 40 evidence work.

## Self-Check: PASSED

- Created summary found: `.planning/phases/39-fail-closed-realtime-meeting-loop/39-03-SUMMARY.md`.
- Modified files found: `saymo/analysis/realtime_gate.py`, `saymo/commands/__init__.py`, `saymo/commands/core.py`, `tests/analysis/test_realtime_gate.py`, and `tests/test_auto_qa_flow.py`.
- Task commits found: `1068d78` and `69fef32`.
- Required focused tests, regression tests, static provider/audio mutation guard, and diff-check results are recorded above.

---
*Phase: 39-fail-closed-realtime-meeting-loop*
*Completed: 2026-07-08*
