# Requirements: Saymo v1.12 F5 Voice Tuning Controls

**Defined:** 2026-07-09
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.12 Requirements

### F5 Pause Presets

- [x] **PAUSE-01**: User can list named F5 pause presets with their sentence,
  clause, paragraph, and silent-breath timing values.
- [x] **PAUSE-02**: User can select a named F5 pause preset per meeting
  profile without hand-editing YAML.
- [x] **PAUSE-03**: User can apply a selected preset so prepared-audio and
  response-cache metadata use the updated F5 pacing fingerprint.

### Voice Timing Review

- [x] **TUNE-01**: User can generate A/B preview WAVs comparing current F5
  timing against a candidate preset without changing the approved voice
  profile.
- [x] **TUNE-02**: User can record a simple preference review for A/B timing
  clips and see which preset/knobs are recommended.
- [x] **TUNE-03**: User can keep preview and review artifacts sanitized, with
  no raw meeting transcript, prompt text, secrets, or training data copied into
  committed files.

### Cache and Review Safety

- [x] **CACHE-01**: User can see an explicit warning when prepared audio or
  response cache is stale and regeneration may be expensive.
- [x] **CACHE-02**: User can choose a targeted prepare/cache command that
  avoids unnecessary regeneration when existing cache artifacts are still
  current.
- [x] **CACHE-03**: User can run `saymo review` without losing the
  prepared-audio voice metadata sidecar required by call-ready checks.
- [x] **CACHE-04**: User can trust response-cache lookup helpers to enforce
  metadata checks consistently across active and legacy code paths.

## Future Requirements

### Voice Naturalness

- **NAT-F01**: User can tune prosody from a richer phrase corpus instead of a
  small preview phrase set.
- **NAT-F02**: User can compare timing presets with automatic speech-rate and
  pause-distribution metrics.
- **NAT-F03**: User can keep separate pause presets per source type, such as
  standup notes versus spontaneous approved answers.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Retraining or fine-tuning the voice model | v1.12 tunes timing controls around the approved F5 voice, not voice identity. |
| Adding audible breath, inhale, hum, or room noise | The live-call boundary remains silent timing only. |
| Deleting or rebuilding all real caches automatically | Existing voice caches and training assets are protected local state; regeneration must be explicit. |
| Switching to another TTS provider | The scope is the current approved local `f5tts_clone` path. |
| Real call transcript export for tuning | Preview/review artifacts must stay sanitized and avoid private meeting text. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PAUSE-01 | Phase 43 | Complete |
| PAUSE-02 | Phase 43 | Complete |
| PAUSE-03 | Phase 43 | Complete |
| TUNE-01 | Phase 43 | Complete |
| TUNE-02 | Phase 43 | Complete |
| TUNE-03 | Phase 43 | Complete |
| CACHE-01 | Phase 44 | Complete |
| CACHE-02 | Phase 44 | Complete |
| CACHE-03 | Phase 44 | Complete |
| CACHE-04 | Phase 44 | Complete |

**Coverage:**
- v1.12 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-07-09*
*Last updated: 2026-07-09 after Phase 44 completion*
