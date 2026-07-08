---
phase: 40-launch-and-realtime-evidence-feedback
plan: "04"
subsystem: evidence-remediation
tags: [saymo, remediation, scorecard, safety-soak, launch-readiness, realtime, docs, pytest]

requires:
  - phase: 40-01
    provides: Read-only launch evidence loader and enriched call-ready artifacts
  - phase: 40-02
    provides: Launch/realtime metrics in session scorecards
  - phase: 40-03
    provides: v1.9 safety-soak violations and totals from scorecard metrics
  - phase: 39-05
    provides: Sanitized realtime decision JSONL evidence and Phase 39 static scope guard
provides:
  - v1.9 remediation hints for scorecard launch/realtime evidence failures
  - v1.9 safety-soak remediation hints with scorecard-first and soak rerun commands
  - Local operator docs for launch/realtime evidence artifacts and privacy limits
  - Static Phase 40 privacy and mutation guards across evidence/reporting modules
affects: [phase-40, EVID-05, remediation, session-scorecard, safety-soak, docs]

tech-stack:
  added: []
  patterns:
    - Remediation hints consume sanitized scorecard and safety-soak metrics only
    - CLI troubleshooting output reuses render_remediation_hints and preserves output-file semantics
    - Static guards cover Phase 40 evidence modules without weakening Phase 39 runtime scope guard

key-files:
  created:
    - docs/LAUNCH-REALTIME-EVIDENCE.md
    - tests/test_launch_realtime_evidence_docs.py
    - .planning/phases/40-launch-and-realtime-evidence-feedback/40-04-SUMMARY.md
  modified:
    - saymo/analysis/remediation.py
    - saymo/analysis/safety_soak.py
    - saymo/commands/tests.py
    - tests/analysis/test_remediation.py
    - tests/test_session_scorecard_cli.py
    - tests/test_safety_soak_cli.py
    - tests/test_realtime_static_guards.py

key-decisions:
  - "v1.9 troubleshooting hints are derived only from sanitized scorecard and safety-soak metrics, artifact paths, log paths, labels, categories, and rerun commands."
  - "safety-soak --scorecard-json inputs are annotated in memory as scorecard-json sources so remediation can print the exact soak rerun path without changing report JSON shape."
  - "session-scorecard and safety-soak keep --output as Markdown output and --json-output as JSON output; remediation remains console troubleshooting output."

patterns-established:
  - "Scorecard remediation adds category-specific launch hints plus one realtime blocker hint using existing RemediationHint rendering."
  - "Safety-soak remediation uses structured source/rule/count detail and guides operators through scorecard JSON regeneration before the soak rerun."
  - "Phase 40 docs and static tests prove reporting remains local, read-only, privacy-safe, and non-mutating."

requirements-completed: [EVID-05]

duration: 8 min
completed: 2026-07-08
---

# Phase 40 Plan 04: Launch and Realtime Evidence Troubleshooting Summary

**Sanitized v1.9 launch/realtime troubleshooting for scorecards and safety-soak, with local operator docs and static evidence guards.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-07-08T19:24:23Z
- **Completed:** 2026-07-08T19:31:56Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Added RED tests for v1.9 remediation hints, CLI troubleshooting output, docs, and Phase 40 static privacy/mutation guards.
- Extended `hints_from_scorecard()` to surface failed launch labels, blocker categories, launch artifact paths, daemon log paths, realtime blocker counts, and exact rerun commands.
- Extended `hints_from_safety_soak()` and safety-soak Markdown next actions with scorecard-first and safety-soak rerun guidance for v1.9 violations.
- Added `docs/LAUNCH-REALTIME-EVIDENCE.md` with local call-ready, session-scorecard, alias, and safety-soak workflow commands plus privacy/read-only limits.

## Task Commits

1. **Task 1 RED: Troubleshooting, docs, and static evidence tests** - `cebfee5` (`test`)
2. **Task 2 GREEN: Implement troubleshooting output, docs, and final validation** - `3b9ff1c` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/remediation.py` - v1.9 scorecard and safety-soak remediation hints.
- `saymo/analysis/safety_soak.py` - v1.9-aware next-action lines in Markdown output.
- `saymo/commands/tests.py` - soft-wrapped remediation output and scorecard-json source path annotation for soak remediation.
- `docs/LAUNCH-REALTIME-EVIDENCE.md` - Local operator workflow and privacy/read-only documentation.
- `tests/analysis/test_remediation.py` - RED/GREEN coverage for scorecard and soak v1.9 hints.
- `tests/test_session_scorecard_cli.py` - CLI coverage for evidence troubleshooting while preserving output files.
- `tests/test_safety_soak_cli.py` - CLI coverage for scorecard-json remediation and failing v1.9 soak output.
- `tests/test_realtime_static_guards.py` - Phase 40 evidence privacy and mutation static guards.
- `tests/test_launch_realtime_evidence_docs.py` - Documentation command and privacy coverage.

## Decisions Made

- Reused the existing `RemediationHint` shape instead of adding a new troubleshooting report type.
- Kept v1.9 hint inputs to sanitized metrics and paths already present in scorecards and soak reports.
- Kept report JSON schemas unchanged; the scorecard JSON path is only attached to in-memory CLI scorecard sources before building a soak report.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RED verification failed as expected with 6 failures across remediation, CLI, and missing docs.
- First focused GREEN run failed on an exact documentation phrase; the doc was adjusted and the focused suite then passed.
- No auth gates, architecture changes, provider repair, audio route mutation, launchd lifecycle mutation, raw transcript analytics, cloud sync, visual dashboard, or live fallback behavior occurred.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_remediation.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py tests/test_realtime_static_guards.py tests/test_launch_realtime_evidence_docs.py -q; test $? -ne 0'`
  - RED result: expected failure, `6 failed, 19 passed in 0.29s`; wrapper exited 0.
- `uv run pytest tests/analysis/test_remediation.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py tests/test_realtime_static_guards.py tests/test_launch_realtime_evidence_docs.py -q`
  - Result: `25 passed in 0.21s`.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/analysis/test_remediation.py tests/test_call_ready_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q`
  - Result: `58 passed in 2.02s`.
- `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/analysis/test_realtime_events.py tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_live_control_cli.py tests/test_realtime_static_guards.py tests/test_call_control_cli.py -q`
  - Result: `108 passed in 3.04s`.
- `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q`
  - Result: `82 passed in 3.47s`.
- `uv run pytest`
  - Result: `540 passed in 6.96s`.
- `bash -lc '! rg "raw_transcript|generated_answer|answer_text|audio_bytes" saymo/analysis/launch_readiness.py saymo/analysis/launch_evidence.py saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/analysis/safety_soak.py saymo/analysis/remediation.py; ! rg "PRIVATE_" saymo/analysis/launch_evidence.py saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/analysis/safety_soak.py saymo/analysis/remediation.py'`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill|bootstrap_argv\\(|bootout_argv\\(|kickstart_argv\\(|append_control_command\\(|run_handbrake_reachability_probe\\(" saymo/analysis/launch_readiness.py saymo/analysis/launch_evidence.py saymo/analysis/realtime_events.py saymo/analysis/session_scorecard.py saymo/analysis/safety_soak.py saymo/analysis/remediation.py'`
  - Result: passed.
- `git diff --check`
  - Result: passed.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 40 now satisfies EVID-01 through EVID-05 in automated coverage. Residual live/manual risk remains limited to real macOS GUI session smoke tests for LaunchAgent state, Accessibility permission, provider tab/mute behavior, BlackHole routing, and actual call audio.

## Self-Check: PASSED

- Created/modified files found: `docs/LAUNCH-REALTIME-EVIDENCE.md`, `tests/test_launch_realtime_evidence_docs.py`, `saymo/analysis/remediation.py`, `saymo/analysis/safety_soak.py`, `saymo/commands/tests.py`, `tests/analysis/test_remediation.py`, `tests/test_session_scorecard_cli.py`, `tests/test_safety_soak_cli.py`, `tests/test_realtime_static_guards.py`, and this summary.
- Task commits found: `cebfee5` and `3b9ff1c`.
- Required RED, focused GREEN, Phase 40 focused, v1.9 regression, safety regression, full suite, static privacy, static mutation, and diff-check results are recorded above.

---
*Phase: 40-launch-and-realtime-evidence-feedback*
*Completed: 2026-07-08*
