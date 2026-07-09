# Requirements: Saymo v1.13 F5 Prosody Metrics

**Defined:** 2026-07-09
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.13 Requirements

### Prosody Corpus

- [x] **CORP-01**: User can use a richer sanitized phrase corpus for F5 timing
  previews that covers short acknowledgements, standup updates, multi-sentence
  answers, clause-heavy responses, and direct handoff replies.
- [x] **CORP-02**: User can generate A/B timing previews from selected corpus
  subsets so current and candidate presets are compared across realistic
  answer shapes.
- [ ] **CORP-03**: User can extend or inspect the preview corpus without
  copying private meeting transcript text, prompts, voice samples, training
  datasets, secrets, or raw audio into committed artifacts.

### Timing Metrics

- [ ] **METR-01**: User can see automatic speech-rate metrics for each preview
  clip, including total duration and a normalized rate suitable for comparing
  timing presets.
- [ ] **METR-02**: User can see pause-distribution metrics grouped by sentence,
  clause, paragraph, and silent-breath continuation pauses.
- [ ] **METR-03**: User can compare current and candidate presets in a
  sanitized report that highlights meaningful pace and pause changes without
  exposing prompt text, response text, audio bytes, private meeting content, or
  secrets.

### Source-Type Presets

- [ ] **SRCE-01**: User can configure separate F5 pause presets per source
  type, such as prepared standup notes, response-cache variants, and
  spontaneous approved answers, without hand-editing YAML for normal changes.
- [ ] **SRCE-02**: User can keep existing profile-level preset behavior when
  no source-type override is configured.
- [ ] **SRCE-03**: User can rely on source-type preset choices participating
  in voice/cache fingerprints so affected prepared audio and response-cache
  artifacts become stale after timing changes.
- [ ] **SRCE-04**: User can see which profile preset and source-type override
  are active in cache-status, review, and readiness diagnostics, with targeted
  regeneration or review commands when artifacts are stale.

## Future Requirements

### Voice Naturalness Automation

- **NAT-F01**: User can get an automatic preset recommendation that combines
  timing metrics with stored preference-review outcomes.
- **NAT-F02**: User can calibrate acceptable speech-rate and pause ranges from
  user-approved benchmark clips.
- **NAT-F03**: User can maintain multiple named corpus packs for different
  meeting styles beyond standup and spontaneous answers.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Retraining or fine-tuning the voice model | v1.13 measures and routes timing around the approved F5 voice, not voice identity. |
| Adding audible breath, inhale, hum, or room noise | The live-call boundary remains silent timing only. |
| Copying real call transcripts into the preview corpus | Corpus and reports must stay sanitized and local-safe. |
| Deleting or rebuilding all real caches automatically | Existing voice caches and training assets are protected local state; regeneration must remain explicit and targeted. |
| Switching to another TTS provider | The scope is the current approved local `f5tts_clone` path. |
| Sending voice clips or metrics to a cloud service | Voice tuning and diagnostics remain local-by-default. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORP-01 | Phase 45 | Complete |
| CORP-02 | Phase 45 | Complete |
| CORP-03 | Phase 45 | Pending |
| METR-01 | Phase 46 | Pending |
| METR-02 | Phase 46 | Pending |
| METR-03 | Phase 46 | Pending |
| SRCE-01 | Phase 47 | Pending |
| SRCE-02 | Phase 47 | Pending |
| SRCE-03 | Phase 47 | Pending |
| SRCE-04 | Phase 47 | Pending |

**Coverage:**
- v1.13 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0
- Duplicate mappings: 0

---
*Requirements defined: 2026-07-09*
*Last updated: 2026-07-09 after completing 45-01*
