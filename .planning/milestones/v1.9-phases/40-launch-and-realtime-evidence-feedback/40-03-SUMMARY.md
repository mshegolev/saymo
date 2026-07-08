---
phase: 40-launch-and-realtime-evidence-feedback
plan: "03"
subsystem: safety-soak-evidence
tags: [saymo, safety-soak, launch-readiness, realtime, scorecard, pytest]

requires:
  - phase: 40-02
    provides: Optional LaunchScorecardMetrics and RealtimeScorecardMetrics on SessionScorecard
  - phase: 39-05
    provides: Sanitized realtime decision labels for cache, provider, fallback, and handbrake blocks
provides:
  - v1.9 safety-soak violations derived only from scorecard launch/realtime metrics
  - v1.9 aggregate totals for launch, cache, daemon, provider, fallback, handbrake, and malformed realtime evidence
  - safety-soak rehearsal pass-through flags for launch/realtime evidence before scorecard aggregation
  - RED/GREEN unit and CLI coverage for unsafe and safe v1.9 evidence gates
affects: [phase-40, EVID-04, safety-soak, scorecard, remediation]

tech-stack:
  added: []
  patterns:
    - Safety-soak remains a scorecard consumer and never reads raw launch/realtime artifacts directly
    - New v1.9 totals are not drift metrics, so old baselines without those keys remain neutral
    - Rehearsal evidence flags are passed only into build_scorecard_from_rehearsal

key-files:
  created:
    - .planning/phases/40-launch-and-realtime-evidence-feedback/40-03-SUMMARY.md
  modified:
    - saymo/analysis/safety_soak.py
    - saymo/commands/tests.py
    - tests/analysis/test_safety_soak.py
    - tests/test_safety_soak_cli.py

key-decisions:
  - "v1.9 safety-soak failures are derived from SessionScorecard launch_metrics and realtime_metrics only."
  - "v1.9 aggregate totals are emitted with zero defaults but kept out of DRIFT_METRICS so old baselines remain neutral."
  - "safety-soak evidence path flags are pass-through for rehearsal scorecard construction, not inputs to safety_soak.py."

patterns-established:
  - "launch_not_ready, stale_or_missing_response_cache, call_control_daemon_not_ready, provider_blocked, fallback_blocked, and handbrake_blocked are independent of legacy would_speak gating."
  - "The v1.9 Markdown totals section appears only when v1.9 metrics are present or nonzero."

requirements-completed: [EVID-04]

duration: 6 min
completed: 2026-07-08
---

# Phase 40 Plan 03: Safety-Soak v1.9 Evidence Gates Summary

**Scorecard-metric safety-soak gates for launch readiness, cache freshness, daemon health, provider drift, fallback blocks, and handbrake blocks.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-08T19:15:31Z
- **Completed:** 2026-07-08T19:20:56Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added RED tests proving safety-soak failed to catch v1.9 launch/cache/daemon/provider/fallback/handbrake evidence before implementation.
- Added v1.9 safety-soak totals and violations from `SessionScorecard.launch_metrics` and `SessionScorecard.realtime_metrics`.
- Added `safety-soak --launch-json/--launch-readiness` and `--realtime-jsonl/--realtime` as rehearsal-only pass-through flags.
- Preserved legacy `--scorecard-json`, `--output`, and `--json-output` semantics, plus old scorecard and old baseline neutrality.

## Task Commits

1. **Task 1 RED: v1.9 safety-soak gate tests** - `5b89837` (`test`)
2. **Task 2 GREEN: Implement v1.9 violations and optional soak pass-through** - `5907b2b` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/safety_soak.py` - v1.9 aggregate totals, metric-only safety violations, and conditional v1.9 Markdown totals.
- `saymo/commands/tests.py` - rehearsal-only launch/realtime evidence flags for safety-soak scorecard construction.
- `tests/analysis/test_safety_soak.py` - unit coverage for unsafe v1.9 evidence, safe v1.9 evidence, and old baseline neutrality.
- `tests/test_safety_soak_cli.py` - CLI coverage for evidence-rich scorecard JSON, output exports, and rehearsal evidence pass-through.
- `.planning/phases/40-launch-and-realtime-evidence-feedback/40-03-SUMMARY.md` - execution evidence and metadata.

## Decisions Made

- v1.9 violations run before the legacy `would_speak` return so launch/realtime blocker evidence fails the gate even when no automatic speech was attempted.
- Launch provider readiness contributes one provider block when explicitly false; realtime provider block counts are added separately.
- Realtime cache blockers include cache miss counts and stable `cache-miss-blocked`, `cache-disabled-blocked`, and `voice-metadata-blocked` labels.
- New v1.9 totals remain outside `DRIFT_METRICS`; old baselines missing these totals are compared only on legacy drift metrics.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RED verification failed as expected with 4 new failures: missing v1.9 violations, missing v1.9 totals, missing nonzero CLI exit for evidence-rich scorecards, and missing safety-soak evidence path flags.
- No auth gates, architecture changes, direct launch/realtime readers in `safety_soak.py`, provider/audio mutations, live provider calls, launchd lifecycle mutations, playback, recording, or config mutation occurred.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_safety_soak.py tests/test_safety_soak_cli.py -q; test $? -ne 0'`
  - RED result: expected failure with `4 failed, 8 passed`; wrapper exited 0.
- `uv run pytest tests/analysis/test_safety_soak.py tests/test_safety_soak_cli.py -q`
  - Result: `12 passed in 0.17s`.
- `uv run pytest tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q`
  - Result: `22 passed in 0.21s`.
- `bash -lc '! rg "load_launch_evidence|load_realtime_decision_events|summarize_realtime_decision_events|launch_json|realtime_jsonl" saymo/analysis/safety_soak.py'`
  - Result: passed.
- `bash -lc '! rg "raw_transcript|generated_answer|answer_text|audio_bytes|PRIVATE_" saymo/analysis/safety_soak.py'`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill|bootstrap_argv\\(|bootout_argv\\(|kickstart_argv\\(|append_control_command\\(|run_handbrake_reachability_probe\\(" saymo/analysis/safety_soak.py'`
  - Result: passed.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/analysis/test_remediation.py tests/test_call_ready_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q`
  - Result: `56 passed in 2.17s`.
- `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/analysis/test_realtime_events.py tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_live_control_cli.py tests/test_realtime_static_guards.py tests/test_call_control_cli.py -q`
  - Result: `105 passed in 3.00s`.
- `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q`
  - Result: `82 passed in 3.45s`.
- `uv run pytest`
  - Result: `533 passed in 6.94s`.
- `bash -lc '! rg "raw_transcript|generated_answer|answer_text|audio_bytes" saymo/analysis/launch_readiness.py saymo/analysis/launch_evidence.py saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/analysis/safety_soak.py saymo/analysis/remediation.py'`
  - Result: passed.
- `bash -lc '! rg "PRIVATE_" saymo/analysis/launch_evidence.py saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/analysis/safety_soak.py saymo/analysis/remediation.py'`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/launch_readiness.py saymo/analysis/launch_evidence.py saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/analysis/safety_soak.py saymo/analysis/remediation.py'`
  - Result: passed.
- `git diff --check`
  - Result: passed.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 40-04 can consume the new v1.9 safety-soak violations and totals for troubleshooting output. Residual live/manual risk remains unchanged: real macOS LaunchAgent, provider tab, audio route, and live-call behavior still require user-session verification outside this automated test run.

## Self-Check: PASSED

- Created/modified files found: `saymo/analysis/safety_soak.py`, `saymo/commands/tests.py`, `tests/analysis/test_safety_soak.py`, `tests/test_safety_soak_cli.py`, and this summary.
- Task commits found: `5b89837` and `5907b2b`.
- Required RED, focused GREEN, cross, safety_soak.py static, Phase 40 focused, v1.9 regression, safety regression, full suite, static privacy, provider/audio mutation, and diff-check results are recorded above.

---
*Phase: 40-launch-and-realtime-evidence-feedback*
*Completed: 2026-07-08*
