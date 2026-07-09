---
phase: 46-timing-metrics-reports
plan: "02"
subsystem: tts
tags: [f5-tts, timing-metrics, preview-artifacts, reports, privacy]

requires:
  - phase: 46-01
    provides: Sanitized F5 preview record metrics with duration, rate, and pause-distribution fields
provides:
  - Metrics-aware `timing-report.md` rendering for F5 preset previews
  - Current-vs-candidate duration, speech-rate, and pause-total deltas
  - Operator docs for the sanitized metrics artifact contract
affects: [f5-presets-preview, f5-timing-review, timing-report, voice-clone-docs]

tech-stack:
  added: []
  patterns:
    - Report rendering reads `record["metrics"]` when present and remains backward-compatible with older records.
    - Delta comparison pairs corpus previews by `corpus.id` and manual previews by `current`/`candidate` labels.

key-files:
  created: []
  modified:
    - saymo/analysis/f5_timing_review.py
    - tests/test_voice_clone_cli.py
    - docs/voice-clone-shootout.md
    - docs/VOICE-NATURALNESS.md

key-decisions:
  - "Timing reports render numeric metadata only: display duration, chars/sec, words/minute, and grouped pause counts/seconds."
  - "Current-vs-candidate deltas use candidate minus current, with measured audio duration preferred over estimated duration when present."
  - "Phase 46 docs and code stay limited to metrics/report evidence; no source-type routing, cache behavior, or preset recommendation logic was added."

patterns-established:
  - "Older preview manifests without `metrics` render `metrics=unavailable` instead of failing."
  - "Delta field names are stable search tokens: `duration_delta`, `chars_per_second_delta`, `words_per_minute_delta`, and `pause_total_delta`."

requirements-completed: [METR-03]

duration: 4 min
completed: 2026-07-09
---

# Phase 46 Plan 02: Timing Metrics Reports Summary

**Sanitized F5 timing reports with per-clip metrics and current-vs-candidate deltas**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-09T20:00:34Z
- **Completed:** 2026-07-09T20:03:58Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Extended `timing-report.md` rendering with duration, chars/sec, words/minute, and pause-distribution summaries for each clip.
- Added a `## Current vs Candidate Deltas` section with duration, rate, and pause-total deltas for corpus and manual preview pairs.
- Preserved artifact privacy and backward compatibility: raw source text remains absent, and older records without metrics render safely.
- Documented the manifest metrics contract, report deltas, measured-duration behavior, and sanitized artifact boundary.

## Task Commits

Each task was committed atomically through the TDD RED/GREEN cycle:

1. **Task 1: Render per-clip metrics and sanitized deltas**
   - `acf8977` test: add failing timing report metrics tests
   - `d6d177e` feat: render F5 timing metrics and deltas
2. **Task 2: Document metrics report contract and privacy boundary**
   - `4f3c454` test: add failing timing docs contract test
   - `28091af` docs: document F5 timing metrics reports

## Files Created/Modified

- `saymo/analysis/f5_timing_review.py` - Renders per-clip metrics, missing-metrics fallback text, and current-vs-candidate delta lines.
- `tests/test_voice_clone_cli.py` - Covers report metrics, delta field names, older manifest compatibility, artifact privacy, and docs contract terms.
- `docs/voice-clone-shootout.md` - Documents manifest metrics, `timing-report.md` deltas, measured WAV duration behavior, and privacy exclusions.
- `docs/VOICE-NATURALNESS.md` - Points F5 preset operators to `timing-report.md` for objective duration, rate, and pause-distribution deltas.

## Verification

- `uv run pytest tests/test_voice_clone_cli.py -q` after Task 1 RED - failed as expected on the missing report section, metric fields, and older-record fallback.
- `uv run pytest tests/test_voice_clone_cli.py -q` after Task 1 GREEN - 15 passed.
- `uv run pytest tests/test_voice_clone_cli.py -q` after Task 2 RED - failed as expected on missing docs metrics terms.
- `uv run pytest tests/analysis/test_f5_timing_metrics.py tests/test_voice_clone_cli.py -q` after Task 2 GREEN - 19 passed.
- Final verification: `uv run pytest tests/analysis/test_f5_timing_metrics.py tests/test_voice_clone_cli.py -q` - 19 passed.
- Acceptance greps confirmed report delta symbols, metrics assertions, raw-text absence assertions, docs metrics terms, docs privacy terms, and no Phase 47/future-scope terms in the renderer or docs.

## Decisions Made

- Deltas are rendered only when both current and candidate records have usable metrics; missing or old metrics render as `metrics=unavailable`.
- Corpus pairs use the sanitized `corpus.id`; manual pairs use the existing `current` and `candidate` labels.
- The report prefers `audio_duration_seconds` for display/delta duration when available, otherwise `estimated_total_duration_seconds`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Auth Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 46 is complete. Timing preview artifacts now provide objective sanitized metrics and reports without adding source-type/cache behavior or preset recommendation scope.

## Self-Check: PASSED

- Found created summary and all modified files listed in this summary.
- Found task commits `acf8977`, `d6d177e`, `4f3c454`, and `28091af`.

---
*Phase: 46-timing-metrics-reports*
*Completed: 2026-07-09*
