---
phase: 47-source-type-pause-presets
plan: "02"
subsystem: tts
tags: [f5tts, pause-presets, source-types, cache-metadata, fingerprints]

requires:
  - phase: 47-01-source-type-pause-presets
    provides: F5 source-type preset vocabulary, resolver helpers, and profile-scoped override persistence
provides:
  - Source-aware F5 selector fingerprints for prepared and response-cache audio
  - Safe source-type preset metadata sidecar fields
  - Prepared/review/response-cache caller wiring with active profile context
  - Response-cache advice, launch, and runtime lookup using response_cache source metadata
affects: [47-03-cache-diagnostics, voice-cache, realtime-response-cache]

tech-stack:
  added: []
  patterns:
    - F5 source-type fingerprinting uses copied config overlays, not runtime config mutation
    - Voice sidecars persist only safe source-type and preset ids
    - Response-cache metadata callers pass active meeting profile plus source_type=response_cache

key-files:
  created: []
  modified:
    - saymo/tts/selector.py
    - saymo/analysis/cache_metadata.py
    - saymo/commands/core.py
    - saymo/commands/tests.py
    - saymo/analysis/cache_advice.py
    - saymo/analysis/launch_cache.py
    - saymo/analysis/realtime_policy.py
    - tests/tts/test_selector.py
    - tests/analysis/test_cache_metadata.py
    - tests/test_review_metadata.py
    - tests/analysis/test_response_cache.py
    - tests/analysis/test_cache_advice.py
    - tests/analysis/test_realtime_policy.py

key-decisions:
  - "Source-type F5 fingerprinting resolves presets on a copied config so metadata changes never mutate loaded runtime config."
  - "Reviewed prepared audio reuses preserved source_profile for preset fingerprinting so review saves keep the prepare-time source context."
  - "prepare-responses now accepts -p/--profile and defaults to standup for backward-compatible response-cache metadata."

patterns-established:
  - "selector_fingerprint_payload accepts optional profile/source_type and adds safe source_preset metadata only for F5 source-aware calls."
  - "VoiceCacheMetadata sidecars remain backward-compatible by defaulting missing source-type preset fields to empty strings."

requirements-completed: [SRCE-03]

duration: 9min
completed: 2026-07-09
---

# Phase 47 Plan 02: Source-Type Preset Fingerprint and Cache Metadata Integration Summary

**F5 prepared-audio and response-cache fingerprints now include source-type pause preset choices through safe, transient metadata wiring.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-07-09T20:34:48Z
- **Completed:** 2026-07-09T20:43:28Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Added source-aware F5 selector fingerprint payloads using `config_with_f5_pause_preset_for_source()` on copied configs.
- Added safe sidecar fields: `source_type`, `source_preset_id`, `profile_preset_id`, and `source_override_preset_id`; old sidecars remain readable.
- Wired prepared, review, response-cache preparation, cache advice, launch readiness, and realtime lookup to pass the active profile and correct source type.
- Added `saymo prepare-responses -p/--profile` for profile-specific response-cache metadata.

## Task Commits

1. **Task 1 RED: Source-aware selector/cache metadata tests** - `446990c` (test)
2. **Task 1 GREEN: Source-aware selector/cache metadata** - `871a60d` (feat)
3. **Task 2 RED: Source-aware caller wiring tests** - `5dc75bb` (test)
4. **Task 2 GREEN: Prepared/review/response-cache caller wiring** - `9007e3f` (feat)

_Both plan tasks followed TDD with RED test commits before implementation commits._

## Files Created/Modified

- `saymo/tts/selector.py` - Added optional `profile` and `source_type` fingerprint inputs and safe F5 `source_preset` payloads.
- `saymo/analysis/cache_metadata.py` - Added safe source-type preset sidecar fields and backward-compatible JSON loading.
- `saymo/commands/core.py` - Wired prepared, review, speak readiness, and realtime startup callers with active profile/source-type metadata.
- `saymo/commands/tests.py` - Added `prepare-responses -p/--profile` and source-aware response-cache metadata in auto-preflight.
- `saymo/analysis/cache_advice.py` - Made prepared and response-cache advice compare source-aware expected metadata.
- `saymo/analysis/launch_cache.py` - Made response-cache launch readiness use active-profile response-cache metadata.
- `saymo/analysis/realtime_policy.py` - Added profile-aware realtime response-cache metadata construction.
- `tests/tts/test_selector.py` - Covered source override and profile fallback selector payloads.
- `tests/analysis/test_cache_metadata.py` - Covered prepared/response-cache source preset staleness, safe fields, and old sidecars.
- `tests/test_review_metadata.py` - Covered prepare/review prepared source metadata and preserved source context.
- `tests/analysis/test_response_cache.py` - Covered profile option, response-cache preparation, and launch readiness source metadata.
- `tests/analysis/test_cache_advice.py` - Covered source-aware prepared and response-cache advice readiness.
- `tests/analysis/test_realtime_policy.py` - Covered runtime response-cache profile/source-type metadata lookup.

## Verification

- `uv run pytest tests/tts/test_selector.py tests/analysis/test_cache_metadata.py tests/test_review_metadata.py tests/analysis/test_response_cache.py tests/analysis/test_cache_advice.py tests/analysis/test_realtime_policy.py -q` -> `56 passed in 0.44s`
- Acceptance greps confirmed prepared and response-cache source-type caller wiring, profile handoff, safe metadata fields, and no new stale-check cache rebuild execution.

## Decisions Made

- Source-aware F5 fingerprinting applies source-type presets only to a copied config before hashing, preserving the loaded runtime config.
- Reviewed audio metadata uses the preserved `source_profile` when available so review saves match the original prepared-audio source context.
- `prepare-responses` defaults `--profile` to `standup`, preserving existing CLI behavior while enabling profile-specific response-cache fingerprints.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used DYLD library fallback for GSD helper commands**
- **Found during:** Execution initialization
- **Issue:** The default Homebrew `node` binary failed to load `/opt/homebrew/opt/llhttp/lib/libllhttp.9.3.dylib`, blocking `gsd-tools.cjs`.
- **Fix:** Ran GSD helper commands with `DYLD_LIBRARY_PATH=/opt/homebrew/Cellar/llhttp/9.3.1/lib`, using the already installed matching llhttp runtime.
- **Files modified:** None
- **Verification:** `gsd-tools.cjs init execute-phase 47-source-type-pause-presets` completed successfully under the fallback.
- **Committed in:** Not applicable; tooling/runtime fallback only.

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Tooling fallback only. No product scope, cache rebuild, synthesis, playback, local asset mutation, retraining, cloud usage, or recommendation behavior was added.

## Issues Encountered

- Response-cache tests initially assumed `config.responses.library` replaces the default response library. Existing behavior merges overrides into defaults, so the GREEN commit refined the test to inspect the intended cached variant while preserving source-profile assertions.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 47-03 can build sanitized cache-status/readiness diagnostics on top of persisted source-type preset ids and source-aware stale reasons. The response-cache and prepared-audio stale checks now detect relevant source-type timing changes without rebuilding or deleting artifacts.

## Self-Check: PASSED

- Summary and all modified files exist.
- Task commits found: `446990c`, `871a60d`, `5dc75bb`, `9007e3f`.
- Fresh verification passed: `uv run pytest tests/tts/test_selector.py tests/analysis/test_cache_metadata.py tests/test_review_metadata.py tests/analysis/test_response_cache.py tests/analysis/test_cache_advice.py tests/analysis/test_realtime_policy.py -q` -> `56 passed in 0.51s`.

---
*Phase: 47-source-type-pause-presets*
*Completed: 2026-07-09*
