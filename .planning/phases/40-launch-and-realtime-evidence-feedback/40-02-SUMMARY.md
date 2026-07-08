---
phase: 40-launch-and-realtime-evidence-feedback
plan: "02"
subsystem: scorecard-evidence
tags: [saymo, realtime, launch-readiness, scorecard, jsonl, pytest, privacy]

requires:
  - phase: 40-01
    provides: Read-only launch evidence loader over enriched and legacy call-ready artifacts
  - phase: 39-05
    provides: Sanitized realtime decision JSONL event schema and append helper
provides:
  - RealtimeEventSummary plus read-only realtime JSONL loading and summarization
  - Optional launch and realtime metrics in SessionScorecard JSON and Markdown
  - session-scorecard evidence flags --launch-json/--launch-readiness and --realtime-jsonl/--realtime
  - Backward-compatible old scorecard JSON loading and no-evidence rendering
affects: [phase-40, EVID-02, EVID-03, scorecard, safety-soak, remediation]

tech-stack:
  added: []
  patterns:
    - JSONL readers tolerate malformed rows and summarize only RealtimeDecisionEvent allowlisted fields
    - Scorecards include Phase 40 evidence only when paths are supplied or missing supplied paths need reporting
    - Old scorecard JSON round-trips without launch_metrics or realtime_metrics

key-files:
  created:
    - .planning/phases/40-launch-and-realtime-evidence-feedback/40-02-SUMMARY.md
  modified:
    - saymo/analysis/realtime_events.py
    - saymo/analysis/session_scorecard.py
    - saymo/commands/tests.py
    - tests/analysis/test_realtime_events.py
    - tests/analysis/test_session_scorecard.py
    - tests/test_session_scorecard_cli.py

key-decisions:
  - "Realtime JSONL loading reconstructs rows through RealtimeDecisionEvent.to_dict() so extra JSON fields cannot enter scorecard summaries."
  - "Scorecard launch/realtime metrics use status=unavailable by default and are omitted from JSON/Markdown unless evidence paths are supplied."
  - "Missing supplied evidence paths produce status=missing metrics and sanitized warnings instead of changing old no-evidence behavior."

patterns-established:
  - "LaunchScorecardMetrics maps LaunchEvidence cache counts, failed labels, daemon readiness, provider readiness, log paths, and rerun command counts into scorecards."
  - "RealtimeScorecardMetrics maps launch-start/end/block labels, cache hit/miss, fallback/provider/handbrake blocks, playback attempts, stop/cancel labels, malformed rows, labels, and sources."
  - "session-scorecard evidence aliases share the same internal launch_json and realtime_jsonl parameters as the canonical flags."

requirements-completed: [EVID-02, EVID-03]

duration: 7 min
completed: 2026-07-08
---

# Phase 40 Plan 02: Realtime and Launch Evidence Scorecards Summary

**Read-only launch and realtime evidence ingestion for session scorecards with backward-compatible JSON/Markdown output.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-08T19:03:37Z
- **Completed:** 2026-07-08T19:10:29Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added `RealtimeEventSummary`, `load_realtime_decision_events()`, and `summarize_realtime_decision_events()` for sanitized JSONL evidence with malformed-row counting.
- Added optional `LaunchScorecardMetrics` and `RealtimeScorecardMetrics` to `SessionScorecard`, including additive JSON and Markdown rendering.
- Added `session-scorecard --launch-json/--launch-readiness` and `--realtime-jsonl/--realtime` without changing existing `--rehearsal`, `--session`, `--output`, or `--json-output` behavior.
- Preserved old scorecard JSON compatibility: no evidence paths means no `launch_metrics`, no `realtime_metrics`, and no v1.9 Markdown section.

## Task Commits

1. **Task 1 RED: Realtime summary and scorecard evidence tests** - `8e34d24` (`test`)
2. **Task 2 GREEN: Implement realtime loaders and optional scorecard metrics** - `525e9a4` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/realtime_events.py` - Realtime JSONL loader, malformed-row tolerance, and summary counters.
- `saymo/analysis/session_scorecard.py` - Optional launch/realtime metric dataclasses, evidence loaders, JSON round-trip support, and v1.9 Markdown section.
- `saymo/commands/tests.py` - Additive session-scorecard evidence path flags and aliases.
- `tests/analysis/test_realtime_events.py` - RED/GREEN coverage for loader sanitization, malformed rows, labels, sources, and Phase 40 summary counters.
- `tests/analysis/test_session_scorecard.py` - RED/GREEN coverage for optional metrics, missing evidence paths, old JSON round-trip, and sanitized Markdown/JSON.
- `tests/test_session_scorecard_cli.py` - RED/GREEN coverage for canonical evidence flags, alias flags, output file semantics, and no-evidence behavior.
- `.planning/phases/40-launch-and-realtime-evidence-feedback/40-02-SUMMARY.md` - Execution evidence and metadata.

## Decisions Made

- Realtime event loading sanitizes by reconstructing `RealtimeDecisionEvent` objects, then counting the stable `to_dict()` payload rather than trusting arbitrary JSON keys.
- `status="unavailable"` remains an internal default and is omitted from JSON/Markdown, while supplied-but-missing paths surface explicit `status="missing"` metrics and warnings.
- The v1.9 Markdown section is appended after the existing Playback and Handbrake section, preserving all existing headings and output meaning when no evidence is supplied.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RED verification failed as expected with `ImportError: cannot import name 'load_realtime_decision_events'`.
- A manual compile probe using bare `python` hit the local pyenv shim (`python: command not found`); rerunning through `uv run python -m py_compile ...` passed. This did not affect required verification.
- No auth gates, architecture changes, provider repair, audio route mutation, launchd lifecycle mutation, preparation, synthesis, playback, recording, or config mutation occurred.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/test_session_scorecard_cli.py -q; test $? -ne 0'`
  - RED result: expected collection failure for missing `load_realtime_decision_events`; wrapper exited 0.
- `uv run pytest tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/test_session_scorecard_cli.py -q`
  - Result: `16 passed in 0.18s`.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/test_session_scorecard_cli.py -q`
  - Result: `30 passed in 1.12s`.
- `uv run pytest tests/test_realtime_static_guards.py tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py -q`
  - Result: `74 passed in 1.80s`.
- `bash -lc '! rg "raw_transcript|generated_answer|answer_text|audio_bytes|PRIVATE_" saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py'`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill|bootstrap_argv\\(|bootout_argv\\(|kickstart_argv\\(|append_control_command\\(|run_handbrake_reachability_probe\\(" saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py'`
  - Result: passed.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/analysis/test_remediation.py tests/test_call_ready_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q`
  - Result: `52 passed in 1.89s`.
- `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/analysis/test_realtime_events.py tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_live_control_cli.py tests/test_realtime_static_guards.py tests/test_call_control_cli.py -q`
  - Result: `105 passed in 2.99s`.
- `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q`
  - Result: `82 passed in 3.45s`.
- `uv run pytest`
  - Result: `529 passed in 7.00s`.
- `bash -lc '! rg "raw_transcript|generated_answer|answer_text|audio_bytes" saymo/analysis/launch_readiness.py saymo/analysis/launch_evidence.py saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/analysis/safety_soak.py saymo/analysis/remediation.py'`
  - Result: passed.
- `bash -lc '! rg "PRIVATE_" saymo/analysis/launch_evidence.py saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/analysis/safety_soak.py saymo/analysis/remediation.py'`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" saymo/analysis/launch_readiness.py saymo/analysis/launch_evidence.py saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/analysis/safety_soak.py saymo/analysis/remediation.py'`
  - Result: passed.
- `git diff --check`
  - Result: passed.
- `uv run python -m py_compile saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/commands/tests.py`
  - Result: passed.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 40-03 can consume scorecard `launch_metrics` and `realtime_metrics` for v1.9 safety-soak violations without rereading raw evidence or probing live provider/audio state.

## Self-Check: PASSED

- Created/modified files found: `saymo/analysis/realtime_events.py`, `saymo/analysis/session_scorecard.py`, `saymo/commands/tests.py`, `tests/analysis/test_realtime_events.py`, `tests/analysis/test_session_scorecard.py`, `tests/test_session_scorecard_cli.py`, and this summary.
- Task commits found: `8e34d24` and `525e9a4`.
- Required RED, focused GREEN, regression, Phase 40, v1.9, safety, full suite, static guard, diff-check, and compile results are recorded above.

---
*Phase: 40-launch-and-realtime-evidence-feedback*
*Completed: 2026-07-08*
