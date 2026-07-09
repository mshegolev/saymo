---
phase: 43-f5-pause-presets-and-a-b-timing-review
plan: "01"
subsystem: f5-pause-presets
tags: [saymo, f5tts, presets, config, fingerprint, pytest]
requirements-completed: [PAUSE-01, PAUSE-02, PAUSE-03]
one-liner: "Added named F5 pause presets, config apply flow, per-profile annotation, and fingerprint integration."
one_liner: "Added named F5 pause presets, config apply flow, per-profile annotation, and fingerprint integration."
completed: 2026-07-09
---

# Phase 43 Plan 01 Summary: F5 Pause Preset Catalog and Apply Flow

**Completed:** 2026-07-09
**Status:** Complete
**Commit:** `51a1782 feat(tts): add F5 pause presets and timing review`

## What Changed

- Added `saymo/tts/f5_presets.py` with the built-in `approved`, `crisp`,
  `calm`, and `deliberate` F5 pause presets.
- Added `tts.f5tts.pause_preset` while keeping the concrete sentence, clause,
  silent-breath, and interval knobs as the runtime/cache-fingerprint contract.
- Added `pause_preset` to the F5 selector fingerprint payload so prepared audio
  and response caches go stale after preset changes.
- Added `saymo f5-presets list`, `show`, and `apply`.
- `apply` updates `config.yaml`, writes the concrete F5 timing knobs, and can
  annotate `meetings.<profile>.voice.f5_pause_preset` without hand-editing YAML.

## Requirement Coverage

| Requirement | Evidence |
|-------------|----------|
| PAUSE-01 | `test_f5_pause_preset_catalog_includes_approved_defaults`, `test_f5_presets_cli_list_show_and_apply_updates_config` |
| PAUSE-02 | `saymo f5-presets apply <preset> --profile <profile>` writes the meeting-profile annotation |
| PAUSE-03 | `test_f5tts_pacing_config_changes_selector_fingerprint_payload` asserts `pause_preset` participates in the fingerprint |

## Notes

No model files, training datasets, reference WAVs, or real caches are modified.
The apply path only edits the selected YAML config.
