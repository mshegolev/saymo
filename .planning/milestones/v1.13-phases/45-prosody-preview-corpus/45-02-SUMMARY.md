---
phase: 45-prosody-preview-corpus
plan: "02"
subsystem: tts
tags: [f5-tts, preview-corpus, click, pytest, privacy]

requires:
  - phase: 45-01
    provides: Built-in sanitized F5 preview corpus and resolver APIs
provides:
  - Selected F5 timing previews from built-in corpus categories
  - Selected F5 timing previews from built-in corpus ids
  - Safe preview record source metadata with corpus id, category, and label only
  - Backward-compatible manual `--text` preview flow
affects: [45-03, f5-presets-preview, f5-timing-review, preview-artifacts]

tech-stack:
  added: []
  patterns:
    - NamedTuple preview item fan-out shared by manual and corpus selections
    - Lazy corpus resolver imports inside Click command paths

key-files:
  created: []
  modified:
    - saymo/commands/voice_clone.py
    - saymo/analysis/f5_timing_review.py
    - tests/test_voice_clone_cli.py

key-decisions:
  - "Preview items share one writer path so manual labels and filenames stay backward-compatible while corpus previews add stable corpus-derived labels."
  - "Corpus preview artifacts expose only source_kind plus corpus id/category/label; raw phrase text remains limited to synthesis and hash/char-count inputs."

patterns-established:
  - "Manual F5 previews use labels and filenames `current-{preset}.wav` and `candidate-{preset}.wav`."
  - "Built-in corpus F5 previews use labels `{entry.id}:current|candidate` and filenames `{entry.id}-current|candidate-{preset}.wav`."

requirements-completed: [CORP-02]

duration: 5 min
completed: 2026-07-09
---

# Phase 45 Plan 02: Selected Corpus Preview Support Summary

**Selected built-in corpus F5 timing previews with sanitized source metadata and stable per-entry clip names**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-09T19:18:16Z
- **Completed:** 2026-07-09T19:23:19Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `source_kind` to F5 timing preview records and optional safe corpus metadata containing exactly id, category, and label.
- Added `saymo f5-presets preview --corpus ...` and `--corpus-id ...` selection controls backed by the built-in corpus resolver.
- Preserved existing manual `--text` preview behavior, including manual labels, filenames, and raw-text-free manifest/report artifacts.
- Added CLI regression coverage for corpus category selection, corpus id selection, conflict errors, missing-selection errors, and privacy assertions.

## Task Commits

Each task was committed atomically through the TDD RED/GREEN cycle:

1. **Task 1: Extend preview records with safe corpus metadata**
   - `65e741b` test: add failing F5 timing metadata tests
   - `6d34bbf` feat: add safe F5 corpus metadata records
2. **Task 2: Add selected corpus preview controls**
   - `017acc8` test: add failing corpus preview CLI tests
   - `d7685a6` feat: add selected corpus F5 previews

## Files Created/Modified

- `saymo/analysis/f5_timing_review.py` - Adds `source_kind` and optional safe corpus metadata to sanitized timing records.
- `saymo/commands/voice_clone.py` - Adds corpus category/id preview selection and fans selected entries into current/candidate records.
- `tests/test_voice_clone_cli.py` - Adds manual and corpus preview regression coverage through the CLI boundary plus focused record-builder checks.

## Verification

- `uv run pytest tests/test_voice_clone_cli.py -q` - 8 passed after Task 1 GREEN.
- `uv run pytest tests/tts/test_f5_preview_corpus.py tests/test_voice_clone_cli.py -q` - 18 passed after Task 2 GREEN and final verification.
- `uv run saymo f5-presets preview --help` - help output includes `--corpus` and `--corpus-id`.
- Acceptance greps confirmed required symbols, test assertions, no raw `"text":` record field, and no Phase 46/47 metric or cache-routing terms.

## Decisions Made

- Preview items share a small local `NamedTuple` so manual and corpus selections use one artifact writer without changing manual preview labels or filenames.
- Corpus previews write only safe metadata (`source_kind`, `corpus.id`, `corpus.category`, `corpus.label`); corpus phrase text is never written to manifest, review, or report artifacts.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for 45-03. The next plan can add stronger artifact privacy regressions and operator docs against the now-supported manual/category/id preview paths.

## Self-Check: PASSED

- Found summary file `.planning/phases/45-prosody-preview-corpus/45-02-SUMMARY.md`.
- Found task commits `65e741b`, `6d34bbf`, `017acc8`, and `d7685a6`.

---
*Phase: 45-prosody-preview-corpus*
*Completed: 2026-07-09*
