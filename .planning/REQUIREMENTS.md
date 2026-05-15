# Requirements: Saymo

**Defined:** 2026-05-15
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1 Requirements

Requirements for milestone v1.0 Speedly Catcher + Speedly Sayer.

### Speedly Catcher

- [ ] **CATCH-01**: User can see catch-path latency for each live window:
  capture, transcription, trigger match, addressing decision, and final action.
- [ ] **CATCH-02**: User can tune capture window length, overlap, cooldown, and
  silence handling per meeting profile without editing source code.
- [ ] **CATCH-03**: User can run offline trigger evaluation against saved call
  samples and see counts for `asked_to_speak`, `question`, `speech`, false
  positives, and misses.
- [ ] **CATCH-04**: User can promote a heard trigger variant from an evaluated
  sample into `vocabulary.fuzzy_expansions` and re-run the evaluation.

### Speedly Sayer

- [ ] **SAY-01**: User can run one preflight command before a call that verifies
  response cache coverage, output device routing, provider readiness, and
  configured profile triggers.
- [ ] **SAY-02**: User can see say-path latency from trigger/hotkey to playback
  start for cached responses.
- [ ] **SAY-03**: User can force prepared playback without waiting for trigger
  detection and receive a clear reason if playback is blocked.
- [ ] **SAY-04**: User can keep auto-mode responsive when response-cache lookup
  misses by using a documented prepared-response fallback.

### Training Loop

- [ ] **TRAIN-01**: User can list captured sample folders and inspect metadata
  without opening raw JSON files manually.
- [ ] **TRAIN-02**: User can replay selected captured samples through a local
  command to validate transcripts and classifications.
- [ ] **TRAIN-03**: User can export a sanitized evaluation report that excludes
  raw audio and private config values.

## v2 Requirements

Deferred to a later milestone.

### Advanced Call Intelligence

- **CALL-01**: User can run speaker-aware trigger evaluation when diarization is
  available locally.
- **CALL-02**: User can train a custom local classifier from accepted/rejected
  trigger samples.
- **CALL-03**: User can run provider-specific end-to-end latency measurement
  inside live Chrome calls.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Required cloud transcription | Violates local-by-default privacy constraint |
| Voice-clone training from call recordings | This milestone is about trigger behavior, not voice identity |
| Fully autonomous meeting agent | Manual takeover and explicit prepared playback remain required safety paths |
| Provider UI redesign | This is CLI/control-path work; provider automation stays behind existing abstractions |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CATCH-01 | Phase 1 | Pending |
| SAY-02 | Phase 1 | Pending |
| CATCH-02 | Phase 2 | Pending |
| CATCH-03 | Phase 2 | Pending |
| CATCH-04 | Phase 2 | Pending |
| SAY-01 | Phase 3 | Pending |
| SAY-03 | Phase 3 | Pending |
| SAY-04 | Phase 3 | Pending |
| TRAIN-01 | Phase 4 | Pending |
| TRAIN-02 | Phase 4 | Pending |
| TRAIN-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-05-15*
*Last updated: 2026-05-15 after creating milestone v1.0 roadmap*
