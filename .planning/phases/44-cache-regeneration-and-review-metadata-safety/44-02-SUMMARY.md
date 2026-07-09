---
phase: 44-cache-regeneration-and-review-metadata-safety
plan: "02"
subsystem: review-and-response-cache-metadata
tags: [saymo, review, cache-metadata, response-cache, pytest]
requirements-completed: [CACHE-03, CACHE-04]
one-liner: "Preserved prepared-audio metadata after review saves and locked stale response-cache lookup behavior."
one_liner: "Preserved prepared-audio metadata after review saves and locked stale response-cache lookup behavior."
completed: 2026-07-09
---

# Phase 44 Plan 02 Summary: Review Sidecar Preservation and Legacy Cache Metadata Checks

**Completed:** 2026-07-09
**Status:** Complete
**Commit:** `15b32b6 feat(cache): add F5 cache regeneration safety checks`

## What Changed

- Added `_write_reviewed_audio_cache()` and wired `saymo review` through it.
- Review saves now write a current prepared-audio `.meta.json` sidecar after
  replacing the reviewed WAV.
- Existing sanitized source fields are preserved when a prior sidecar exists.
- Added response-cache tests proving both `lookup()` and
  `get_variant_by_key()` refuse stale WAVs when `voice_metadata` is configured.

## Requirement Coverage

| Requirement | Evidence |
|-------------|----------|
| CACHE-03 | `test_write_reviewed_audio_cache_writes_current_sidecar_without_text`, `test_write_reviewed_audio_cache_preserves_existing_source_fields` |
| CACHE-04 | `test_lookup_refuses_stale_voice_metadata`, `test_get_variant_by_key_refuses_stale_voice_metadata` |

## Notes

No response-cache implementation change was required for the lookup guards; the
new tests codify existing `_variant_ready()` behavior across both runtime paths.
