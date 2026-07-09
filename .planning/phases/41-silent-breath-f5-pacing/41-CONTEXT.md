---
phase: 41-silent-breath-f5-pacing
type: context
status: ready_for_execution
created: 2026-07-09
autonomous: true
requirements: [F5P-01, F5P-02, F5P-03, F5P-04, F5P-05]
depends_on:
  - v1.8-call-ready-voice-clone
  - v1.10-natural-pacing-preview-feedback
---

# Phase 41 Context: Silent Breath F5 Pacing

## Goal

Remove audible breath, hum, and buzz from the F5 natural pacing output while
preserving the timing behavior that makes the voice feel like it takes air
before continuing.

## Approved Design Direction

The user explicitly approved the natural pacing work, then rejected the audible
breath layer after listening to the preview. The new boundary is:

- keep sentence and clause pauses;
- keep longer breath-like pauses at paragraph/continuation points;
- do not transmit any reference-sample breath audio into the microphone output;
- keep the implementation local and inside the existing `f5tts_clone` path;
- do not retrain, redownload, or mutate voice datasets.

## Existing Code Insights

### Reusable Assets

- `saymo.tts.f5tts.F5TTSCloneTTS` owns F5 subprocess synthesis and WAV output.
- `saymo.tts.naturalness.prepare_for_natural_pacing()` adds conservative
  pause markers for dash, semicolon, and non-time colon boundaries.
- `saymo.tts.naturalness.split_for_tts()` splits spoken chunks, paragraph
  breaks, and explicit `[pause:N]` markers.
- `tests/tts/test_f5tts.py` already uses fake chunk WAVs so natural pacing can
  be tested without real F5 inference.

### Established Patterns

- Voice quality changes are verified with focused unit tests plus a real local
  preview for ear-based review.
- Local user config under `~/.saymo/config.yaml` is not committed, but can be
  updated after making a timestamped backup.
- Expensive voice assets and training datasets are not mutated unless the user
  explicitly asks.

### Integration Points

- `F5TTSConfig` exposes the knobs that load from YAML.
- `config.example.yaml` documents user-visible defaults.
- `docs/VOICE-NATURALNESS.md` records the rationale so future tuning does not
  reintroduce audible breath samples.

## Required User-Facing Outcomes

1. F5 natural pacing output contains silence at breath points, not non-zero
   breath/noise samples.
2. Sentence and clause pauses continue to work.
3. Silent breath timing is configurable separately from sentence/clause timing.
4. Focused tests prove the silent-breath contract.
5. A short local preview exists for the user to review with `afplay`.

## Deferred Ideas

- Per-profile prosody presets.
- Automated old/new A/B benchmark reports.
- Voice-model retraining.

