---
phase: 40-launch-and-realtime-evidence-feedback
plan: "01"
subsystem: launch-evidence
tags: [saymo, call-ready, launch-readiness, evidence, pytest, privacy]

requires:
  - phase: 36-call-ready-preflight-and-cache-gate
    provides: LaunchReadinessReport.to_dict, call-ready artifacts, and grouped remediation
  - phase: 37-provider-and-audio-remediation
    provides: provider/audio readiness rows and non-destructive call-ready contract
  - phase: 38-local-call-control-daemon-and-launchagent
    provides: call-control daemon/log path readiness rows
  - phase: 39-fail-closed-realtime-meeting-loop
    provides: fail-closed realtime boundary and sanitized evidence constraints
provides:
  - Read-only LaunchEvidence dataclass, loader, and summary over launch artifacts
  - Backward-compatible enriched call-ready artifact JSON with schema metadata
  - Legacy LaunchReadinessReport.to_dict JSON loading with normalized evidence summaries
  - CLI compatibility coverage for --json, --output, and --json --output
affects: [phase-40, EVID-01, call-ready, launch-evidence, scorecard, safety-soak]

tech-stack:
  added: []
  patterns:
    - Read-only artifact loaders consume saved JSON instead of rerunning launch checks
    - call-ready artifact files keep legacy root fields and add only optional Phase 40 metadata
    - launch evidence summaries use sanitized check metadata, labels, counts, paths, and rerun commands

key-files:
  created:
    - saymo/analysis/launch_evidence.py
    - .planning/phases/40-launch-and-realtime-evidence-feedback/40-01-SUMMARY.md
  modified:
    - saymo/analysis/launch_readiness.py
    - tests/analysis/test_launch_readiness.py
    - tests/test_call_ready_cli.py

key-decisions:
  - "Launch evidence is a read-only artifact consumer; it does not import or call live provider, audio, launchd, probe, preparation, synthesis, playback, recording, or config mutation helpers."
  - "call-ready --output writes enriched root-level JSON, while call-ready --json continues printing the legacy report.to_dict payload without artifact_path or schema metadata."
  - "Legacy launch-readiness JSON loads with schema_version=legacy and derives normalized summaries from sanitized check rows."

patterns-established:
  - "LaunchEvidence summarizes failed labels, block categories, cache counts, voice fingerprints, provider status, daemon status/log paths, artifact paths, rerun commands, and sanitized checks."
  - "Artifact path extraction is deterministic: root artifact path first, then stdout/stderr daemon log paths before other metadata paths."
  - "Sensitive metadata field names are redacted during launch-readiness serialization and launch-evidence loading without storing forbidden names in source."

requirements-completed: [EVID-01]

duration: 12 min
completed: 2026-07-08
---

# Phase 40 Plan 01: Launch Evidence Artifact Summary

**Read-only launch evidence loader with backward-compatible enriched call-ready artifacts over sanitized readiness checks.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-08T18:45:32Z
- **Completed:** 2026-07-08T18:57:14Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `saymo.analysis.launch_evidence` with `LaunchEvidence`, `load_launch_evidence()`, and `summarize_launch_evidence()` over saved launch-readiness JSON.
- Enriched `write_launch_readiness_artifact()` output with `schema_version`, `evidence_kind`, `mode`, `artifact_path`, and `created_at` while preserving legacy root fields and sorted JSON with trailing newline.
- Preserved `call-ready --json`, `--output`, and `--json --output` compatibility: JSON stdout remains pure legacy report JSON, and human output prints `artifact: PATH` only outside JSON mode.
- Added coverage for legacy artifact loading, failed labels, blocker categories, cache counts, voice fingerprints, provider and daemon status, artifact/log paths, rerun commands, privacy redaction, and non-mutation guards.

## Task Commits

1. **Task 1 RED: Launch evidence schema and call-ready artifact tests** - `6de7399` (`test`)
2. **Task 2 GREEN: Implement launch evidence loader and artifact writer** - `bd4d849` (`feat`)

_Note: TDD tasks produced separate RED and GREEN commits._

## Files Created/Modified

- `saymo/analysis/launch_evidence.py` - Read-only launch artifact loader and normalized evidence summary dataclass.
- `saymo/analysis/launch_readiness.py` - Enriched artifact writer and stricter sensitive field-name redaction.
- `tests/analysis/test_launch_readiness.py` - Launch evidence loader, legacy artifact, summary, privacy, and artifact schema tests.
- `tests/test_call_ready_cli.py` - CLI compatibility assertions for enriched output artifacts and pure JSON stdout.
- `.planning/phases/40-launch-and-realtime-evidence-feedback/40-01-SUMMARY.md` - Execution evidence and metadata.

## Decisions Made

- Kept `LaunchReadinessReport.to_dict()` as the source of truth for `profile`, `provider`, `ready`, counts, and `checks`; Phase 40 metadata is additive only.
- Kept evidence loading deterministic and read-only: it uses `json.loads()` plus structured dictionaries and never imports the launch collector or runtime helpers.
- Treated daemon log paths as launch evidence paths for both enriched and legacy artifacts because legacy check metadata already contains those sanitized paths.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Contract] Corrected rich fixture count and legacy path expectations**
- **Found during:** Task 2 GREEN focused verification.
- **Issue:** The RED fixture expected `block_count=4` even though it contained five failed blocking checks, and the legacy artifact test expected only the loader path even though daemon log paths are valid sanitized evidence in legacy check metadata.
- **Fix:** Updated the tests to expect five blocking rows and to include stdout/stderr daemon log paths for legacy evidence; made path extraction deterministic in the loader.
- **Files modified:** `tests/analysis/test_launch_readiness.py`, `saymo/analysis/launch_evidence.py`
- **Verification:** Focused, remediation, Phase 40, v1.9 regression, safety regression, full suite, static guard, and diff-check validation passed.
- **Committed in:** `bd4d849`

---

**Total deviations:** 1 auto-fixed (Rule 1 test contract)
**Impact on plan:** No scope expansion; the fix aligned the tests with the planned evidence semantics.

## Issues Encountered

- RED verification failed as expected with missing `saymo.analysis.launch_evidence` and missing Phase 40 artifact fields.
- No auth gates, architecture decisions, provider repair, audio route mutation, launchd lifecycle mutation, preparation, synthesis, playback, recording, or config mutation occurred.

## Verification Commands

- `bash -lc 'uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q; test $? -ne 0'`
  - RED result: expected failure, `6 failed, 17 passed in 2.11s`; wrapper exited 0.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
  - Result: `23 passed in 1.94s`.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/analysis/test_remediation.py -q`
  - Result: `28 passed in 1.86s`.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/analysis/test_remediation.py tests/test_call_ready_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q`
  - Result: `45 passed in 2.00s`.
- `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/analysis/test_realtime_events.py tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_live_control_cli.py tests/test_realtime_static_guards.py tests/test_call_control_cli.py -q`
  - Result: `103 passed in 2.99s`.
- `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q`
  - Result: `82 passed in 3.40s`.
- `uv run pytest`
  - Result: `522 passed in 7.67s`.
- `bash -lc '! rg "raw_transcript|generated_answer|answer_text|audio_bytes" saymo/analysis/launch_readiness.py saymo/analysis/launch_evidence.py; ! rg "PRIVATE_" saymo/analysis/launch_evidence.py'`
  - Result: passed.
- `bash -lc '! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill|bootstrap_argv\\(|bootout_argv\\(|kickstart_argv\\(|append_control_command\\(|run_handbrake_reachability_probe\\(" saymo/analysis/launch_evidence.py'`
  - Result: passed.
- Phase-wide privacy and provider/audio mutation guards from `40-VALIDATION.md`
  - Result: passed.
- `git diff --check`
  - Result: passed.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 40 can now feed launch evidence into realtime/session scorecards without rerunning call-ready checks. EVID-02 and EVID-03 remain for Plan 40-02.

## Self-Check: PASSED

- Created/modified files found: `saymo/analysis/launch_evidence.py`, `saymo/analysis/launch_readiness.py`, `tests/analysis/test_launch_readiness.py`, `tests/test_call_ready_cli.py`, and this summary.
- Task commits found: `6de7399` and `bd4d849`.
- Verification outputs and required static guard command strings are recorded above.

---
*Phase: 40-launch-and-realtime-evidence-feedback*
*Completed: 2026-07-08*
