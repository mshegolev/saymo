# Requirements: Saymo v1.10 Silent Breath Natural Pacing

**Defined:** 2026-07-09
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.10 Requirements

### F5 Natural Pacing

- [x] **F5P-01**: User can generate F5 natural pacing output where breath
  moments are silent pauses and do not contain audible hum, buzz, or breath
  samples.
- [x] **F5P-02**: User can keep sentence and clause pauses while disabling
  audio breath splicing for live-call microphone output.
- [x] **F5P-03**: User can configure silent breath timing separately from
  sentence and clause pause timing.
- [x] **F5P-04**: User can verify with automated tests that breath points in a
  stitched F5 WAV are zero-valued silence, not non-zero reference-sample audio.
- [x] **F5P-05**: User can produce a short local F5 preview for ear-based review
  of the silent-breath pacing behavior.

## Future Requirements

### F5 Natural Pacing

- **F5P-F01**: User can select alternate prosody presets per meeting profile.
- **F5P-F02**: User can compare old/new pacing through an automated A/B
  benchmark report.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Retraining or fine-tuning the voice model | The issue is an output pacing/noise artifact, not missing identity training. |
| Using call recordings as voice-clone training data | Existing privacy and training-data boundaries remain unchanged. |
| Adding audible inhale effects for live calls | User explicitly wants the behavior to feel like breathing without transmitting breath/noise. |
| New cloud voice providers | The active path remains local F5-TTS. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| F5P-01 | Phase 41 | Complete |
| F5P-02 | Phase 41 | Complete |
| F5P-03 | Phase 41 | Complete |
| F5P-04 | Phase 41 | Complete |
| F5P-05 | Phase 41 | Complete |

**Coverage:**
- v1.10 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0

---
*Requirements defined: 2026-07-09*
*Last updated: 2026-07-09 after phase verification*
