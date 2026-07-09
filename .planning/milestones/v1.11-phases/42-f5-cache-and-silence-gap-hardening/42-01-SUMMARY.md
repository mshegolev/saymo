---
phase: 42-f5-cache-and-silence-gap-hardening
plan: "01"
subsystem: f5-natural-pacing
tags: [saymo, f5tts, cache-metadata, silent-breath, pytest]
requirements-completed: [F5G-01, F5G-02, F5G-03, F5G-04, F5G-05, F5G-06]
one-liner: "Hardened F5 cache invalidation and silent-breath regression coverage without changing runtime synthesis behavior."
one_liner: "Hardened F5 cache invalidation and silent-breath regression coverage without changing runtime synthesis behavior."
completed: 2026-07-09
---

# Phase 42 Plan 01 Summary: F5 Cache and Silence Gap Hardening

**Completed:** 2026-07-09
**Status:** Complete
**Commit:** `2eac8e1 test(tts): harden F5 cache and silence gaps`

## What Changed

- Added prepare-cache metadata coverage proving F5 pacing knob changes make an
  older prepared WAV sidecar stale with `voice_metadata_stale`.
- Added response-cache coverage proving all stale response variants are reported
  with sanitized `intent[index]:voice_metadata_stale` diagnostics.
- Added deterministic F5 continuation-pause coverage for
  `breath_interval_sentences`, verifying the continuation gap is zero-valued
  silence.
- Added static guards proving `saymo/tts/f5tts.py` does not use
  `load_breath_sample()` or `breath_gain`.
- Tightened voice-naturalness docs so audible breath splicing is scoped to
  non-F5 engines while F5 live-call breath behavior remains silent timing.

## Accomplishments

- Hardened F5 cache invalidation and silent-breath regression coverage without
  changing runtime synthesis behavior.

## Requirement Coverage

| Requirement | Evidence |
|-------------|----------|
| F5G-01 | `test_prepare_metadata_goes_stale_when_f5_pacing_changes` |
| F5G-02 | `test_response_cache_reports_stale_when_f5_pacing_changes` |
| F5G-03 | cache and response-cache stale tests assert no private text/audio leakage |
| F5G-04 | `test_f5tts_natural_pacing_uses_silent_breath_pause_for_continuation_interval` |
| F5G-05 | `test_f5_live_call_path_does_not_use_audible_breath_samples` |
| F5G-06 | `test_f5_voice_naturalness_docs_define_breath_as_silent_timing` |

## Notes

No runtime synthesis code was changed. The tests codify the v1.10 runtime
contract and the documentation wording was clarified where the new static guard
found ambiguity.
