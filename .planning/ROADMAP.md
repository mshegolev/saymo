# Roadmap: Saymo

## Overview

Milestone v1.1 builds on the completed Speedly Catcher/Sayer work. The next
focus is Advanced Call Intelligence: captured samples should explain speaker
context, learned trigger confidence, and provider-specific latency without
requiring cloud services or risky live-call behavior changes.

## Milestones

- ✅ **v1.0 Speedly Catcher + Speedly Sayer** - Phases 1-4 (complete)
- 📋 **v1.1 Call Intelligence Loop** - Phases 5-7 (planned)

## Phases

**Phase Numbering:**
- Integer phases (5, 6, 7): Planned milestone work
- Decimal phases (6.1, 6.2): Urgent insertions

- [ ] **Phase 5: Speaker-Aware Sample Loop** - Add local speaker labels to
  captured samples and make trigger evaluation speaker-aware.
- [ ] **Phase 6: Local Trigger Classifier** - Let accepted/rejected samples
  train and shadow-test a lightweight local classifier.
- [ ] **Phase 7: Provider Latency Probe** - Measure provider-specific
  end-to-end latency inside active Chrome calls.

## Phase Details

### Phase 5: Speaker-Aware Sample Loop
**Goal**: Let the user label who spoke in captured windows and evaluate trigger
behavior separately for `me`, `other`, and `unknown` speakers.
**Depends on**: v1.0 sample review workflow
**Requirements**: SPK-01, SPK-02, SPK-03
**Success Criteria** (what must be TRUE):
  1. User can set or correct a speaker label on a saved sample from CLI.
  2. Trigger evaluation groups counts, misses, and false positives by speaker.
  3. Existing samples without labels remain valid as `unknown`.
  4. No cloud diarization dependency is required.
**Plans**: 3 plans

Plans:
- [ ] 05-01: Add speaker label metadata support
- [ ] 05-02: Make trigger evaluation speaker-aware
- [ ] 05-03: Add sample label review commands and docs

### Phase 6: Local Trigger Classifier
**Goal**: Train a local sample-based classifier from accepted/rejected trigger
decisions and compare it against deterministic gating before it affects calls.
**Depends on**: Phase 5
**Requirements**: CLF-01, CLF-02, CLF-03
**Success Criteria** (what must be TRUE):
  1. User can mark a sample answer decision accepted or rejected from CLI.
  2. Training refuses to run until minimum labeled-data thresholds are met.
  3. Classifier artifacts are stored locally and can be inspected or deleted.
  4. `trigger-eval` and `trigger-check` can show classifier shadow confidence
     without changing answer decisions.
**Plans**: 3 plans

Plans:
- [ ] 06-01: Add accepted/rejected sample labels
- [ ] 06-02: Train lightweight local trigger classifier
- [ ] 06-03: Add shadow-mode classifier diagnostics

### Phase 7: Provider Latency Probe
**Goal**: Measure end-to-end latency for active Chrome call providers so the
user can distinguish audio/STT delays from provider mute/playback delays.
**Depends on**: Phase 6
**Requirements**: LAT-01, LAT-02, LAT-03
**Success Criteria** (what must be TRUE):
  1. User can run one provider-latency probe for the configured profile.
  2. The probe reports capture, transcription, trigger, unmute, playback-start,
     playback duration, and mute-recovery segments.
  3. Results can be exported as local JSON/Markdown history by profile/provider.
  4. A failed provider step reports a blocked reason without leaving auto-mode
     state ambiguous.
**Plans**: 3 plans

Plans:
- [ ] 07-01: Add provider latency probe command
- [ ] 07-02: Capture segmented provider/playback timings
- [ ] 07-03: Add latency history export and docs

## Progress

**Execution Order:**
Phases execute in numeric order: 5 → 6 → 7

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 5. Speaker-Aware Sample Loop | v1.1 | 0/3 | Not started | - |
| 6. Local Trigger Classifier | v1.1 | 0/3 | Not started | - |
| 7. Provider Latency Probe | v1.1 | 0/3 | Not started | - |
