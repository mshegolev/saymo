---
phase: 46-timing-metrics-reports
plan: "01"
subsystem: tts
tags: [f5-tts, timing-metrics, preview-artifacts, pytest, privacy]

requires:
  - phase: 45-02
    provides: Selected corpus preview controls and safe corpus metadata in F5 timing artifacts
  - phase: 45-03
    provides: Artifact privacy regression boundary for manifest, review JSON, and timing report
provides:
  - Deterministic F5 timing metrics helper for dry-run and measured preview records
  - Sanitized per-record duration, speech-rate, and pause-distribution metrics
  - Optional measured WAV duration handoff for non-dry-run F5 timing previews
affects: [46-02, f5-presets-preview, f5-timing-review, timing-report]

tech-stack:
  added: []
  patterns:
    - Metrics are built from the same `prepare_for_natural_pacing()` and `split_for_tts()` path used by F5 synthesis.
    - Dry-run preview metrics stay deterministic by estimating spoken duration from sanitized spoken chunk counts.

key-files:
  created:
    - saymo/analysis/f5_timing_metrics.py
    - tests/analysis/test_f5_timing_metrics.py
  modified:
    - saymo/analysis/f5_timing_review.py
    - saymo/commands/voice_clone.py
    - tests/test_voice_clone_cli.py

key-decisions:
  - "F5 preview metrics are numeric summaries only: duration, measured duration when available, spoken counts, rate fields, and grouped pause totals."
  - "Pause accounting reuses the existing F5 natural-pacing splitter so comma handling and clause markers stay aligned with live synthesis."
  - "Dry-run rate comparisons use estimated duration, while non-dry-run records use measured WAV duration when supplied."

patterns-established:
  - "Every new F5 timing preview record includes a `metrics` object while older manifests without metrics remain accepted by preference recording."
  - "Pause distribution groups are exactly `sentence`, `clause`, `paragraph`, and `silent_breath`."

requirements-completed: [METR-01, METR-02]

duration: 4 min
completed: 2026-07-09
---

# Phase 46 Plan 01: F5 Timing Metrics Contract and Record Integration Summary

**Deterministic F5 timing metrics embedded in sanitized preview records with optional measured WAV duration**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-09T19:45:54Z
- **Completed:** 2026-07-09T19:50:33Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `build_f5_timing_metrics()` with deterministic estimated duration, optional measured duration, spoken char/word counts, chars/sec, words/minute, and grouped pause distribution.
- Attached metrics to every new F5 timing preview record without persisting raw manual or corpus text.
- Measured non-dry-run WAV duration with `soundfile` after writing synthesized audio and passed it into the sanitized record builder.
- Added focused helper tests plus CLI artifact tests proving dry-run metrics are JSON-safe and raw text remains absent.

## Task Commits

Each task was committed atomically through the TDD RED/GREEN cycle:

1. **Task 1: Add deterministic F5 timing metrics helper**
   - `d054dec` test: add failing F5 timing metrics tests
   - `670c2ad` feat: implement F5 timing metrics helper
2. **Task 2: Attach metrics to preview records and measured WAV duration**
   - `a7dc25c` test: add failing preview metrics integration tests
   - `8d2efed` feat: attach metrics to F5 timing previews

## Files Created/Modified

- `saymo/analysis/f5_timing_metrics.py` - Builds JSON-safe duration, rate, and pause-distribution metrics from F5 timing settings and natural-pacing chunks.
- `tests/analysis/test_f5_timing_metrics.py` - Covers the metrics contract, pause group counts, rounding, JSON serialization, and raw-text absence.
- `saymo/analysis/f5_timing_review.py` - Adds `audio_duration_seconds` to `build_f5_timing_record()` and embeds `record["metrics"]`.
- `saymo/commands/voice_clone.py` - Measures non-dry-run WAV duration with `soundfile` and passes it to the timing record builder.
- `tests/test_voice_clone_cli.py` - Adds CLI coverage for metrics in dry-run corpus preview artifacts and direct builder coverage for measured duration.

## Verification

- `uv run pytest tests/analysis/test_f5_timing_metrics.py -q` - 3 passed after Task 1 GREEN.
- `uv run pytest tests/analysis/test_f5_timing_metrics.py tests/test_voice_clone_cli.py -q` - 17 passed after Task 2 GREEN and final verification.
- Dry-run artifact inspection: `saymo f5-presets preview calm --corpus-id standup-blocked --dry-run` produced 2 manifest records, each with `metrics`, `audio_duration_seconds: null`, and all four pause groups; raw corpus phrase text was absent from `manifest.json`, `review.json`, and `timing-report.md`.
- Acceptance greps confirmed required metrics symbols, natural-pacing helper usage, no `load_breath_sample`, no `source_type`, no cache/fingerprint behavior, and no automatic recommendation logic.

## Decisions Made

- F5 timing metrics stay deterministic for dry-run by estimating spoken duration from spoken character count divided by `14.0 * f5_speed`.
- Rate fields use measured audio duration when present; otherwise they use the estimated total duration.
- Pause metrics count natural-pacing chunks the same way `F5TTSCloneTTS._synthesize_natural_sync()` materializes silence, including separate paragraph and silent-breath continuation buckets.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The first Task 1 GREEN run exposed a test-fixture mismatch: ASCII hyphen is not a clause marker in `prepare_for_natural_pacing()`. The test was aligned to the existing em-dash clause-pause contract, and the helper then passed the planned verification.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for 46-02. Preview records now carry sanitized numeric metrics that the next plan can render in `timing-report.md` with current-vs-candidate deltas.

## Self-Check: PASSED

- Found created and modified files listed in this summary.
- Found task commits `d054dec`, `670c2ad`, `a7dc25c`, and `8d2efed`.

---
*Phase: 46-timing-metrics-reports*
*Completed: 2026-07-09*
