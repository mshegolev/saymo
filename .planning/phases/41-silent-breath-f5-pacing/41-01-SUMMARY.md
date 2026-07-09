---
phase: 41-silent-breath-f5-pacing
plan: "01"
subsystem: f5-natural-pacing
tags: [saymo, f5tts, tts, natural-pacing, silent-breath, pytest]

requires:
  - Phase 41 context and requirements
provides:
  - silent breath pauses in F5 natural pacing
  - test coverage for zero-valued breath pause output
  - local F5 preview for ear review
affects: [F5P-01, F5P-02, F5P-03, F5P-04, F5P-05]

key-files:
  created:
    - tests/tts/test_naturalness.py
    - docs/superpowers/specs/2026-07-09-f5-natural-pacing-design.md
    - docs/superpowers/plans/2026-07-09-f5-natural-pacing.md
  modified:
    - saymo/tts/f5tts.py
    - saymo/tts/naturalness.py
    - saymo/config.py
    - config.example.yaml
    - docs/VOICE-NATURALNESS.md
    - tests/tts/test_f5tts.py
    - tests/test_config.py

requirements-completed: [F5P-01, F5P-02, F5P-03, F5P-04, F5P-05]
completed: 2026-07-09
---

# Phase 41 Plan 01: Silent Breath F5 Pacing Summary

## Accomplishments

- Added conservative F5 text prosody preparation for dash, semicolon, and
  non-time colon pauses while preserving commas.
- Added F5 batch chunk synthesis so natural pacing loads the F5 model once for
  multiple spoken chunks.
- Replaced audible breath splicing with silent breath pauses.
- Added `silent_breath_pause_seconds` and removed `breath_gain` from the F5
  config path.
- Updated local `~/.saymo/config.yaml` after creating
  `~/.saymo/config.yaml.bak-20260709-silent-breath`.
- Generated preview:
  `~/.saymo/voice_benchmarks/20260709-silent-breath/f5tts-silent-breath-01.wav`.

## Evidence

- RED test failed on the previous non-zero breath samples:
  `test_f5tts_natural_pacing_uses_silent_breath_pause_for_paragraph_break`.
- GREEN focused suite passed: `32 passed`.
- TTS suite passed: `64 passed`.
- Full suite passed: `551 passed`.
- Preview sanity check found `longest_quiet_s=0.753`, confirming a silent
  pause exists in the real generated WAV.

## Commits

- `77e91c1 docs: start milestone v1.10 silent breath natural pacing`
- `15b5ede feat(tts): add silent F5 natural pacing`

## User Review

Listen with:

```bash
afplay ~/.saymo/voice_benchmarks/20260709-silent-breath/f5tts-silent-breath-01.wav
```

If timing feels too long or too short, tune `silent_breath_pause_seconds`,
`sentence_pause_seconds`, or `clause_pause_seconds`.

