---
phase: 36-call-ready-preflight-and-cache-gate
plan: "02"
subsystem: launch-readiness
tags: [saymo, pytest, call-ready, obsidian, prepared-audio, cache-metadata, privacy]

requires:
  - phase: 36-01
    provides: shared LaunchReadinessCheck and LaunchReadinessReport contracts
  - phase: 34-call-ready-engine-selector-and-fallback-chain
    provides: privacy-safe voice cache metadata checks
provides:
  - Importable daily-note path, ensure, and source-inspection helpers
  - Daily-note presence and usable source launch-readiness checks
  - Source-aware prepared standup audio metadata and launch blocker
affects: [phase-36, phase-39, call-ready, launch-gate, prepared-audio]

tech-stack:
  added: []
  patterns:
    - Privacy-safe SHA-256 source digests for prepared audio freshness
    - Package-owned Obsidian daily-note creation with script delegation
    - Launch-source checks wired through the shared readiness collector

key-files:
  created:
    - saymo/analysis/launch_sources.py
    - .planning/phases/36-call-ready-preflight-and-cache-gate/36-02-SUMMARY.md
  modified:
    - saymo/analysis/launch_readiness.py
    - saymo/obsidian/daily_notes.py
    - scripts/ensure_obsidian_daily_note.py
    - saymo/analysis/cache_metadata.py
    - saymo/commands/core.py
    - tests/analysis/test_launch_readiness.py
    - tests/analysis/test_cache_metadata.py

key-decisions:
  - "Daily-note file existence and usable standup source readiness are separate blocking checks."
  - "Prepared standup audio freshness uses source SHA-256 metadata, not raw note or generated answer text."
  - "Check-only launch readiness never creates notes or synthesizes audio; creation remains behind --prepare."

patterns-established:
  - "DailyNoteReadiness carries only path/count/hash/reason fields and never note text."
  - "VoiceCacheMetadata optional source fields are ignored unless an expected source_sha256 is provided."
  - "PreparedAudioStatus reports sanitized path, source, and stale reason metadata for launch gates."

requirements-completed: [LAUN-02, LAUN-03, LAUN-04]

duration: 6 min
completed: 2026-07-08
---

# Phase 36 Plan 02: Daily Source and Prepared Audio Summary

**Daily-note source readiness and prepared standup audio freshness now block launch using privacy-safe source digests.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-08T13:02:34Z
- **Completed:** 2026-07-08T13:09:33Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Moved daily-note path creation, idempotent ensure behavior, and source inspection into `saymo.obsidian.daily_notes`.
- Added `daily_note_present`, `daily_note_source_ready`, and `prepared_standup_audio` blocking checks to the shared launch-readiness collector.
- Extended voice cache metadata with optional `source_kind`, `source_profile`, and `source_sha256` fields, with stale source checks returning `source_metadata_stale`.
- Updated `saymo prepare` and team prepare to write source-aware prepared WAV sidecars without storing raw note or generated answer text.

## Task Commits

1. **Task 1: Move daily-note creation into package helpers and add source readiness checks** - `6067454` (`feat`)
2. **Task 2 RED: Add source metadata readiness tests** - `d393a1e` (`test`)
3. **Task 2 GREEN: Add source-aware prepared WAV metadata checks** - `c6502a4` (`feat`)

_Note: Task 1 used the RED tests seeded by 36-01; Task 2 added and committed a focused RED update before implementation._

## Files Created/Modified

- `saymo/analysis/launch_sources.py` - daily-note and prepared-audio readiness dataclasses and collectors.
- `saymo/analysis/launch_readiness.py` - wires launch source checks into the shared report collector.
- `saymo/obsidian/daily_notes.py` - importable daily-note path, ensure, template, config loader, and privacy-safe source inspection.
- `scripts/ensure_obsidian_daily_note.py` - CLI wrapper delegating to package helpers while still printing only the note path.
- `saymo/analysis/cache_metadata.py` - source digest fields and `source_metadata_stale` validation.
- `saymo/commands/core.py` - source digest calculation and metadata writes during prepare/team prepare.
- `tests/analysis/test_launch_readiness.py` - prepared-audio source metadata readiness expectation.
- `tests/analysis/test_cache_metadata.py` - source digest and stale-source metadata regression.

## Verification Commands

- `uv run pytest tests/scripts/test_ensure_obsidian_daily_note.py tests/analysis/test_launch_readiness.py::test_placeholder_daily_note_blocks_source_readiness tests/test_call_ready_cli.py::test_call_ready_prepare_creates_note_without_overwrite -q` - RED before Task 1 implementation: 2 failed, 3 passed; missing daily-note source check and missing `--prepare` note creation.
- `uv run pytest tests/scripts/test_ensure_obsidian_daily_note.py tests/analysis/test_launch_readiness.py::test_placeholder_daily_note_blocks_source_readiness tests/test_call_ready_cli.py::test_call_ready_prepare_creates_note_without_overwrite -q` - PASS after Task 1: 5 passed.
- `uv run pytest tests/analysis/test_launch_readiness.py::test_prepared_audio_requires_current_metadata_and_source_digest tests/analysis/test_cache_metadata.py -q` - RED before Task 2 implementation: 2 failed, 2 passed; missing prepared-audio check and `source_sha256`.
- `uv run pytest tests/analysis/test_launch_readiness.py::test_prepared_audio_requires_current_metadata_and_source_digest tests/analysis/test_cache_metadata.py -q` - PASS after Task 2: 4 passed.
- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q` - PASS: 10 passed.
- `uv run pytest tests/scripts/test_ensure_obsidian_daily_note.py tests/analysis/test_launch_readiness.py::test_placeholder_daily_note_blocks_source_readiness tests/analysis/test_launch_readiness.py::test_prepared_audio_requires_current_metadata_and_source_digest tests/analysis/test_cache_metadata.py tests/test_call_ready_cli.py::test_call_ready_prepare_creates_note_without_overwrite -q` - PASS: 9 passed.

## Decisions Made

- Used `daily_note_source_ready` and `prepared_standup_audio` as the plan-level launch keys.
- Compared source freshness only when an expected `source_sha256` is present, preserving compatibility with older sidecars and non-source-aware checks.
- Kept `call-ready` check-only mode read-only: no note creation, no `_prepare`, no synthesis, and no provider/audio mutation.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

Concurrent 36-03 execution advanced `main` and updated shared planning files while 36-02 was running. The 36-02 commits continued on the current HEAD without reverting or staging the other agent's work.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for 36-04 to wire grouped remediation/artifacts across the now-present daily-note, prepared-audio, response-cache, and cloned-voice launch checks. Phase 36-03 already completed concurrently.

## Self-Check: PASSED

- Created/modified files found: `saymo/analysis/launch_sources.py`, `saymo/obsidian/daily_notes.py`, `scripts/ensure_obsidian_daily_note.py`, `saymo/analysis/cache_metadata.py`, `saymo/commands/core.py`, `tests/analysis/test_launch_readiness.py`, `tests/analysis/test_cache_metadata.py`, and this summary.
- Task commits found: `6067454`, `d393a1e`, `c6502a4`.

---
*Phase: 36-call-ready-preflight-and-cache-gate*
*Completed: 2026-07-08*
