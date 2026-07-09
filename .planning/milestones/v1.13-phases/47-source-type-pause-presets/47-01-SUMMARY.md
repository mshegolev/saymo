---
phase: 47-source-type-pause-presets
plan: "01"
subsystem: tts
tags: [f5tts, pause-presets, source-types, cli, config]

requires:
  - phase: 46-timing-metrics-reports
    provides: Sanitized F5 timing metrics and preview/report evidence
provides:
  - F5 source-type preset vocabulary and resolver helpers
  - Profile-scoped source-type preset YAML persistence via CLI
  - Public config example for prepared, response_cache, and spontaneous overrides
affects: [47-02-source-type-fingerprints, 47-03-cache-diagnostics]

tech-stack:
  added: []
  patterns:
    - Profile voice config stores source-type pause preset overrides
    - Source-specific CLI writes avoid mutating global F5 timing fields

key-files:
  created:
    - tests/tts/test_f5_source_presets.py
  modified:
    - saymo/config.py
    - saymo/tts/f5_presets.py
    - saymo/commands/voice_clone.py
    - tests/test_voice_clone_cli.py
    - config.example.yaml

key-decisions:
  - "Source-type overrides live under meetings.<profile>.voice.f5_pause_presets and never rewrite global F5 timing."
  - "Preset resolution falls back from source override to profile f5_pause_preset to global tts.f5tts.pause_preset."

patterns-established:
  - "F5 source types are a closed vocabulary: prepared, response_cache, spontaneous."
  - "Resolver helpers return copied configs for source-specific timing without mutating loaded runtime config."

requirements-completed: [SRCE-01, SRCE-02]

duration: 5min
completed: 2026-07-09
---

# Phase 47 Plan 01: Source-Type Pause Presets Summary

**F5 pause presets can now be resolved and persisted per answer source while preserving profile and global fallback behavior.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-09T20:23:06Z
- **Completed:** 2026-07-09T20:27:34Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added source-type resolver helpers for `prepared`, `response_cache`, and `spontaneous`.
- Preserved fallback order: source override -> profile `f5_pause_preset` -> global `tts.f5tts.pause_preset`.
- Added `saymo f5-presets apply --source-type` for profile-scoped YAML overrides only.
- Documented public source-type override syntax in `config.example.yaml`.

## Task Commits

1. **Task 1 RED: Source-type resolver tests** - `12e957e` (test)
2. **Task 1 GREEN: Source-type resolver and profile fallback** - `d54a7ce` (feat)
3. **Task 2 RED: Source-type CLI tests** - `a5bc616` (test)
4. **Task 2 GREEN: Source-type CLI persistence** - `810d4a8` (feat)

_Note: Both plan tasks were TDD tasks, so each has a RED test commit and a GREEN implementation commit._

## Files Created/Modified

- `saymo/config.py` - Added `MeetingProfile.voice` so `meetings.<profile>.voice` is preserved.
- `saymo/tts/f5_presets.py` - Added source-type constants, normalization, purpose mapping, resolver dataclass, and non-mutating copied-config helper.
- `saymo/commands/voice_clone.py` - Added `f5-presets apply --source-type` with validation and profile-scoped YAML writes.
- `tests/tts/test_f5_source_presets.py` - Added resolver, fallback, validation, and non-mutation tests.
- `tests/test_voice_clone_cli.py` - Added CLI persistence and error/no-partial-write tests.
- `config.example.yaml` - Added commented source-type preset syntax.

## Verification

- `uv run pytest tests/tts/test_f5_source_presets.py tests/test_voice_clone_cli.py -q` -> `26 passed in 0.34s`
- Task acceptance greps confirmed required resolver symbols, `MeetingProfile.voice`, source-type examples/assertions, and no new `load_breath_sample`, retrain, cloud, cache rebuild, fingerprint, or automatic recommendation logic in plan scope.

## Decisions Made

- Source-specific CLI writes update only `meetings.<profile>.voice.f5_pause_presets.<source_type>`, leaving `tts.f5tts` and profile-level `f5_pause_preset` unchanged.
- Source-type validation is shared through `normalize_f5_source_type()` so CLI and resolver failures list all valid choices.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used installed Node 20 for GSD helper commands**
- **Found during:** Execution initialization
- **Issue:** The default Homebrew `node` binary failed to load `libllhttp.9.3.dylib`, blocking `gsd-tools.cjs`.
- **Fix:** Ran GSD helper commands with `PATH=/opt/homebrew/opt/node@20/bin:$PATH`, using the already installed working Node 20 runtime.
- **Files modified:** None
- **Verification:** `gsd-tools.cjs init execute-phase 47-source-type-pause-presets` completed successfully under Node 20.
- **Committed in:** Not applicable; tooling/runtime fallback only.

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Tooling fallback only. No product scope, dependency, cache, retraining, audible breath, cloud, or recommendation behavior was added.

## Issues Encountered

- Default `/opt/homebrew/bin/node` is currently broken because it links to missing `libllhttp.9.3.dylib`. The plan used `/opt/homebrew/opt/node@20/bin/node` for GSD tooling.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 47-02 can use `resolve_f5_pause_preset_for_source()` and `config_with_f5_pause_preset_for_source()` to include source-specific timing in fingerprints without mutating the loaded config.

## Self-Check: PASSED

- Summary and all created/modified files exist.
- Task commits found: `12e957e`, `d54a7ce`, `a5bc616`, `810d4a8`.
- Fresh verification passed: `uv run pytest tests/tts/test_f5_source_presets.py tests/test_voice_clone_cli.py -q` -> `26 passed in 0.34s`.

---
*Phase: 47-source-type-pause-presets*
*Completed: 2026-07-09*
