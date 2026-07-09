---
phase: 44-cache-regeneration-and-review-metadata-safety
plan: "01"
subsystem: cache-regeneration-advice
tags: [saymo, cache-status, f5tts, remediation, pytest]
requirements-completed: [CACHE-01, CACHE-02]
one-liner: "Added read-only cache status advice with explicit F5 cost warnings and targeted repair commands."
one_liner: "Added read-only cache status advice with explicit F5 cost warnings and targeted repair commands."
completed: 2026-07-09
---

# Phase 44 Plan 01 Summary: Stale-Cache Cost Warnings and Targeted Repair Commands

**Completed:** 2026-07-09
**Status:** Complete
**Commit:** `15b32b6 feat(cache): add F5 cache regeneration safety checks`

## What Changed

- Added `saymo.analysis.cache_advice` with read-only prepared-audio and
  response-cache advice.
- Added `saymo cache-status -p <profile>` to show prepared/response cache
  status, explicit F5 regeneration warnings, and targeted commands.
- Updated launch-readiness response-cache actions to explain expensive F5
  regeneration and avoid unnecessary `--force`.
- Updated auto-preflight/rehearsal remediation hints to distinguish prepared
  audio regeneration from response-cache preparation.

## Requirement Coverage

| Requirement | Evidence |
|-------------|----------|
| CACHE-01 | `test_prepared_audio_cache_advice_warns_for_stale_f5_metadata`, `test_response_cache_advice_warns_for_stale_or_missing_variants`, `test_cache_status_cli_warns_with_targeted_commands` |
| CACHE-02 | cache advice and remediation tests assert `saymo prepare -p <profile>` vs `saymo prepare-responses` targeted commands |

## Notes

`cache-status`, preflight, and call-ready remain read-only. They do not delete,
regenerate, or rewrite cache files.
