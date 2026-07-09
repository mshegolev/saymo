# Requirements: Saymo v1.11 F5 Gap Hardening

**Defined:** 2026-07-09
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.11 Requirements

### F5 Gap Hardening

- [ ] **F5G-01**: User can verify prepared standup audio metadata created
  before an F5 pacing change is treated as stale after any F5 pacing knob
  changes.
- [ ] **F5G-02**: User can verify response-cache metadata created before an
  F5 pacing change is treated as stale after any F5 pacing knob changes.
- [ ] **F5G-03**: User can verify F5 pacing cache-staleness diagnostics report
  stable reasons such as `voice_metadata_stale` without exposing prompt text,
  response text, audio bytes, or private meeting content.
- [ ] **F5G-04**: User can verify `breath_interval_sentences` continuation
  pauses in F5 natural pacing are zero-valued silence, not non-zero
  breath/noise samples.
- [ ] **F5G-05**: User can run a regression or static guard proving the F5
  live-call synthesis path does not import, call, or splice
  `load_breath_sample()` output.
- [ ] **F5G-06**: User can read the voice-naturalness documentation and config
  examples and see that F5 live-call "breath" behavior means silent timing,
  not audible breath injection.

## Future Requirements

### F5 Natural Pacing

- **F5G-F01**: User can select named F5 pause presets per meeting profile.
- **F5G-F02**: User can compare old and new F5 pacing through an automated A/B
  benchmark report.
- **F5G-F03**: User can get an operator warning when cached audio is stale and
  expensive regeneration is required before a meeting.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Retuning pause durations by ear | v1.11 closes hardening gaps; subjective timing can be adjusted later without changing contracts. |
| Retraining or fine-tuning the voice model | The known gaps are cache/test/guard coverage, not voice identity. |
| Deleting real prepared audio or response caches | This milestone should prove invalidation behavior without destructive cleanup. |
| Adding audible inhale effects | The active live-call boundary remains silent breath timing only. |
| New cloud voice providers | The hardening scope is the local F5 path. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| F5G-01 | Phase 42 | Pending |
| F5G-02 | Phase 42 | Pending |
| F5G-03 | Phase 42 | Pending |
| F5G-04 | Phase 42 | Pending |
| F5G-05 | Phase 42 | Pending |
| F5G-06 | Phase 42 | Pending |

**Coverage:**
- v1.11 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0

---
*Requirements defined: 2026-07-09*
*Last updated: 2026-07-09 after milestone definition*
