---
phase: 45-prosody-preview-corpus
plan: "01"
subsystem: tts
tags: [f5-tts, preview-corpus, click, pytest]

requires:
  - phase: 44
    provides: F5 pause presets and sanitized timing preview flow
provides:
  - Built-in sanitized F5 preview corpus with stable ids, categories, labels, and generic text
  - Resolver APIs for corpus listing, category listing, id lookup, and category/id selection
  - `saymo f5-presets corpus list` command that displays safe corpus metadata only
affects: [45-02, 45-03, f5-presets-preview, f5-timing-review]

tech-stack:
  added: []
  patterns:
    - Frozen dataclass corpus entries with tuple-based stable ordering
    - Lazy CLI imports under existing Click command groups

key-files:
  created:
    - saymo/tts/f5_corpus.py
    - tests/tts/test_f5_preview_corpus.py
  modified:
    - saymo/commands/voice_clone.py
    - tests/test_voice_clone_cli.py

key-decisions:
  - "Corpus inspection CLI lists only ids, categories, and labels; phrase text remains API-only for later preview synthesis."

patterns-established:
  - "F5 preview corpus APIs preserve canonical metadata while accepting trimmed case-insensitive selections."
  - "CLI corpus inspection stays read-only and config-independent beyond standard command bootstrap."

requirements-completed: [CORP-01]

duration: 3 min
completed: 2026-07-09
---

# Phase 45 Plan 01: Built-in Sanitized F5 Preview Corpus Summary

**Stable synthetic F5 preview corpus with metadata-only CLI inspection**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-09T19:09:35Z
- **Completed:** 2026-07-09T19:13:09Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `saymo.tts.f5_corpus` with five required answer-shape categories and at least two entries per category.
- Added resolver helpers for stable listing, category discovery, id lookup, and category/id selection.
- Added `saymo f5-presets corpus list`, rendering only corpus id, category, and label metadata.
- Added focused pytest coverage for corpus contracts and CLI output privacy.

## Task Commits

Each task was committed atomically through the TDD RED/GREEN cycle:

1. **Task 1: Add the built-in sanitized corpus module**
   - `99add1e` test: add failing corpus contract tests
   - `a9d9931` feat: add built-in F5 preview corpus
2. **Task 2: Add `saymo f5-presets corpus list`**
   - `b556654` test: add failing corpus CLI list test
   - `bac0186` feat: add F5 preview corpus list command

## Files Created/Modified

- `saymo/tts/f5_corpus.py` - Built-in corpus entries and resolver APIs.
- `tests/tts/test_f5_preview_corpus.py` - Corpus category, lookup, selection, and error-message tests.
- `saymo/commands/voice_clone.py` - Nested `f5-presets corpus list` command.
- `tests/test_voice_clone_cli.py` - CLI test proving metadata is shown and phrase text is not printed.

## Verification

- `uv run pytest tests/tts/test_f5_preview_corpus.py -q` - 7 passed.
- `uv run pytest tests/tts/test_f5_preview_corpus.py tests/test_voice_clone_cli.py -q` - 13 passed.
- Acceptance greps confirmed required symbols, categories, command hooks, CLI test assertions, and no phrase text in the CLI implementation.

## Decisions Made

Corpus inspection is intentionally metadata-only: operators can inspect stable ids, categories, and labels from the CLI, while the phrase text stays behind the corpus API for later preview generation work.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for 45-02. The next plan can reuse `resolve_f5_preview_corpus_selection()` to generate selected corpus subset previews while keeping artifacts sanitized.

## Self-Check: PASSED

- Found created/modified files listed in this summary.
- Found task commits `99add1e`, `a9d9931`, `b556654`, and `bac0186`.

---
*Phase: 45-prosody-preview-corpus*
*Completed: 2026-07-09*
