---
phase: 45-prosody-preview-corpus
plan: "03"
subsystem: tts
tags: [f5-tts, preview-corpus, privacy, docs, pytest]

requires:
  - phase: 45-02
    provides: Selected corpus preview controls and safe corpus metadata in artifacts
provides:
  - Final regression proving corpus and manual F5 preview artifacts omit raw source text
  - Operator docs for corpus inspection, category previews, id previews, and artifact privacy
  - Naturalness guide pointer to repeatable sanitized F5 corpus tuning
affects: [f5-presets-preview, preview-artifacts, voice-docs, phase-46, phase-47]

tech-stack:
  added: []
  patterns:
    - Artifact privacy tests concatenate manifest, review, and timing report files before checking absence
    - Docs present built-in corpus preview as the repeatable sanitized baseline and manual text as one-off local preview

key-files:
  created:
    - .planning/phases/45-prosody-preview-corpus/45-03-SUMMARY.md
  modified:
    - tests/test_voice_clone_cli.py
    - docs/voice-clone-shootout.md
    - docs/VOICE-NATURALNESS.md

key-decisions:
  - "Repeatable F5 timing tuning docs point operators to built-in corpus selections first; manual text is documented as one-off local preview."
  - "Final artifact regression treats manifest.json, review.json, and timing-report.md as the persisted privacy boundary for raw source text."

patterns-established:
  - "Preview artifact privacy tests inspect every persisted timing-preview review file before asserting raw manual and corpus text absence."
  - "Corpus preview docs describe only hashes/counts, timing snapshots, paths, and safe corpus id/category/label metadata."

requirements-completed: [CORP-03]

duration: 2 min
completed: 2026-07-09
---

# Phase 45 Plan 03: Artifact Privacy Regression and Operator Docs Summary

**F5 corpus preview docs plus end-to-end artifact privacy regression for corpus and manual preview text**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-09T19:28:04Z
- **Completed:** 2026-07-09T19:30:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `test_f5_presets_corpus_preview_artifacts_omit_raw_text`, covering corpus id previews from `standup-blocked` and manual `--text` previews.
- Verified `manifest.json`, `review.json`, and `timing-report.md` retain safe corpus metadata while omitting raw corpus phrase text and raw manual preview text.
- Updated the voice clone shootout guide with `saymo f5-presets corpus list`, `--corpus standup`, `--corpus-id standup-blocked`, and explicit artifact privacy rules.
- Updated the naturalness guide to point F5 live-call pacing tuning at the sanitized corpus path.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add final raw-text absence regression** - `a9a41c6` (test)
2. **Task 2: Document corpus preview workflow and privacy rules** - `27cca60` (docs)

## Files Created/Modified

- `tests/test_voice_clone_cli.py` - Adds the final artifact privacy regression across corpus and manual preview runs.
- `docs/voice-clone-shootout.md` - Documents corpus inspection, selected corpus previews, manual one-off previews, and safe artifact metadata.
- `docs/VOICE-NATURALNESS.md` - Points F5 live-call pacing tuning to the repeatable sanitized corpus workflow.
- `.planning/phases/45-prosody-preview-corpus/45-03-SUMMARY.md` - Records plan execution, verification, and state handoff.

## Verification

- `uv run pytest tests/test_voice_clone_cli.py -q` - 12 passed after Task 1 and after Task 2.
- `uv run pytest tests/tts/test_f5_preview_corpus.py tests/test_voice_clone_cli.py -q` - 19 passed.
- `rg -n "test_f5_presets_corpus_preview_artifacts_omit_raw_text|PRIVATE MANUAL PREVIEW TEXT|standup-blocked" tests/test_voice_clone_cli.py` - found required regression markers.
- `rg -n "entry\\.text|manifest\\.json|review\\.json|timing-report\\.md" tests/test_voice_clone_cli.py` - found required artifact and raw-text assertions.
- `rg -n "f5-presets corpus list|--corpus standup|--corpus-id standup-blocked|corpus_id|text_sha256|text_chars" docs/voice-clone-shootout.md docs/VOICE-NATURALNESS.md` - found required docs markers.
- `rg -n "speech-rate|pause-distribution|source-type|automatic preset recommendation|cache fingerprint routing" docs/voice-clone-shootout.md docs/VOICE-NATURALNESS.md` - no matches.

## Decisions Made

- Built-in corpus previews are documented as the preferred repeatable tuning path; manual text previews remain available but are explicitly framed as one-off local checks.
- Artifact privacy coverage now treats the manifest, editable review JSON, and timing report as one combined persisted boundary.

## Deviations from Plan

None - plan executed within the requested file scope and no auto-fixes were needed.

## Issues Encountered

- The Task 1 TDD RED run passed immediately because Plan 45-02 had already implemented raw-text-free artifacts. No production code change was required; the task completed as a test-only hardening regression.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 45 is complete. Phase 46 can add objective timing metrics on top of sanitized corpus preview artifacts without changing the raw-text privacy boundary.

---
*Phase: 45-prosody-preview-corpus*
*Completed: 2026-07-09*

## Self-Check: PASSED

- Found created/modified files listed in this summary.
- Found task commits `a9a41c6` and `27cca60`.
