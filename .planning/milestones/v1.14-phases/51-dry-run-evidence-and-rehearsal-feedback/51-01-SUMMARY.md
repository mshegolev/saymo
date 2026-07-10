---
phase: 51-dry-run-evidence-and-rehearsal-feedback
plan: "01"
subsystem: testing
tags: [pytest, dry-run, launch-evidence, rehearsal, scorecard, safety-soak]

requires:
  - phase: 50-provider-audio-and-call-control-health
    provides: Dry-run provider/audio/control readiness checks and safe rerun guidance
  - phase: 49-source-prepared-audio-cache-and-voice-readiness
    provides: Dry-run source/cache/voice readiness metadata and non-mutating repair guidance
  - phase: 48-dry-run-orchestrator-and-result-contract
    provides: Read-only `saymo dry-run` command and launch-readiness artifact writer
provides:
  - RED contracts for sanitized dry-run launch evidence artifacts
  - RED contracts for normalized dry-run evidence comparison and flat compare CLI
  - RED contracts for rehearsal-recorded launch evidence reuse in scorecard and safety-soak
affects: [51-02, dry-run, launch-evidence, rehearsal, session-scorecard, safety-soak]

tech-stack:
  added: []
  patterns:
    - "RED-only pytest contracts use temp JSON launch evidence and monkeypatched reports."
    - "Private sentinel fixtures cover transcript, prompt, response, audio, secret, voice sample, and training-data leakage."
    - "Rehearsal, scorecard, and safety-soak contracts reference saved dry-run artifacts without running dry-run."

key-files:
  created:
    - tests/analysis/test_launch_evidence.py
    - .planning/phases/51-dry-run-evidence-and-rehearsal-feedback/51-01-SUMMARY.md
  modified:
    - tests/test_dry_run_cli.py
    - tests/test_rehearsal_cli.py
    - tests/test_session_scorecard_cli.py
    - tests/test_safety_soak_cli.py

key-decisions:
  - "Kept Plan 51-01 strictly RED/test-only; production code remains untouched for Plan 51-02."
  - "Used only `tmp_path` JSON fixtures and monkeypatched launch-readiness reports; no real dry-run, TTS, audio, provider, launchd, model, cache, or protected asset command was run."
  - "Pinned the flat `dry-run-compare` command shape and comparison API names expected by the GREEN plan."

patterns-established:
  - "Dry-run evidence tests assert complete flat launch-readiness artifact fields plus private-content exclusion."
  - "Comparison tests assert improved, regressed, mixed, invalid-file, JSON, and human-rendering contracts over normalized launch evidence."
  - "Rehearsal artifacts must store compact `launch_evidence` summaries, while scorecard and safety-soak must reload the recorded path through the existing evidence loader."

requirements-covered-red: [EVID-01, EVID-02, EVID-03]

duration: 5min
completed: 2026-07-10
---

# Phase 51 Plan 01: Dry-Run Evidence And Rehearsal Feedback RED Summary

**Sanitized dry-run artifacts, read-only evidence comparison, and rehearsal/scorecard/safety-soak evidence reuse are now locked as failing RED pytest contracts for Plan 51-02.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-10T14:29:00Z
- **Completed:** 2026-07-10T14:34:16Z
- **Tasks:** 2
- **Files modified:** 5 test files plus this summary

## Accomplishments

- Added `tests/analysis/test_launch_evidence.py` with dry-run launch evidence loading, comparison semantics, JSON rendering, text rendering, invalid-file, and redaction contracts.
- Extended `tests/test_dry_run_cli.py` with complete sanitized artifact assertions, broader private sentinels, static non-destructive guards, and a flat `dry-run-compare` CLI contract.
- Extended rehearsal CLI tests so `--launch-json` must load dry-run evidence, print compact non-private status, record compact `launch_evidence`, and warn on missing evidence without rerunning dry-run.
- Extended session-scorecard tests so explicit dry-run launch evidence and rehearsal-recorded launch evidence paths must both load into sanitized launch metrics.
- Extended safety-soak tests so rehearsal-recorded dry-run launch evidence must drive launch, cache, provider, and daemon gate failures.

## Files Created/Modified

- `tests/analysis/test_launch_evidence.py` - New RED comparison/loading/redaction contracts.
- `tests/test_dry_run_cli.py` - Adds dry-run artifact completeness/privacy and `dry-run-compare` CLI contracts.
- `tests/test_rehearsal_cli.py` - Adds `--launch-json` rehearsal evidence recording and missing-evidence warning contracts.
- `tests/test_session_scorecard_cli.py` - Adds dry-run launch evidence acceptance and rehearsal-recorded fallback contracts.
- `tests/test_safety_soak_cli.py` - Adds safety-soak gate contract using rehearsal-recorded dry-run evidence.
- `.planning/phases/51-dry-run-evidence-and-rehearsal-feedback/51-01-SUMMARY.md` - Documents RED execution.

## Verification

Command:

```bash
uv run pytest tests/analysis/test_launch_evidence.py tests/test_dry_run_cli.py tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q
```

Result: RED, expected non-zero.

Summary: `9 failed, 20 passed in 0.45s`.

Failure reasons:

- Missing `compare_launch_evidence_paths`, `launch_evidence_comparison_to_json`, and `render_launch_evidence_comparison` in `saymo.analysis.launch_evidence`.
- Missing flat `dry-run-compare` command registration.
- `saymo dry-run --output` does not yet redact the new prompt/response/voice/training sentinel fields from human/artifact output.
- `saymo rehearsal` does not yet accept `--launch-json`.
- `session-scorecard --rehearsal <artifact-with-launch-evidence>` does not yet load the rehearsal-recorded launch evidence path.
- `safety-soak --rehearsal <artifact-with-launch-evidence>` does not yet pick up dry-run launch evidence through scorecard construction.

## Deviations from Plan

None - plan executed as RED/test-only. The only adjustment was keeping the scorecard dry-run fixture to a single dry-run rerun command so it matches the plan contract exactly.

## Safety Notes

- No production code was edited.
- No real `saymo dry-run` was run against local state.
- No audio/TTS/provider/launchd/model/cache commands were run.
- No protected `.saymo` assets, voice samples, training datasets, checkpoints, prepared audio, or response caches were read or modified.
- All evidence inputs were temporary JSON fixtures under pytest `tmp_path`.

## Authentication Gates

None.

## Issues Encountered

None. The pytest failures are the expected RED state for missing Plan 51-02 implementation.

## Next Phase Readiness

Plan 51-02 can now implement normalized launch evidence comparison, the flat `dry-run-compare` CLI, expanded artifact redaction, rehearsal `--launch-json`, and rehearsal-recorded launch evidence fallback for scorecard and safety-soak.

---
*Phase: 51-dry-run-evidence-and-rehearsal-feedback*
*Completed: 2026-07-10*

## Self-Check: PASSED

- Found `tests/analysis/test_launch_evidence.py`.
- Found `tests/test_dry_run_cli.py`.
- Found `tests/test_rehearsal_cli.py`.
- Found `tests/test_session_scorecard_cli.py`.
- Found `tests/test_safety_soak_cli.py`.
- Found `.planning/phases/51-dry-run-evidence-and-rehearsal-feedback/51-01-SUMMARY.md`.
- RED verification command ran and failed for intended missing implementation contracts, not syntax errors.
