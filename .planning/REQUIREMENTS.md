# Requirements: Saymo

**Defined:** 2026-05-15
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1 Requirements

Requirements for milestone v1.0 Speedly Catcher + Speedly Sayer.

### Speedly Catcher

- [x] **CATCH-01**: User can see catch-path latency for each live window:
  capture, transcription, trigger match, addressing decision, and final action.
- [x] **CATCH-02**: User can tune capture window length, overlap, cooldown, and
  silence handling per meeting profile without editing source code.
- [x] **CATCH-03**: User can run offline trigger evaluation against saved call
  samples and see counts for `asked_to_speak`, `question`, `speech`, false
  positives, and misses.
- [x] **CATCH-04**: User can promote a heard trigger variant from an evaluated
  sample into `vocabulary.fuzzy_expansions` and re-run the evaluation.

### Speedly Sayer

- [x] **SAY-01**: User can run one preflight command before a call that verifies
  response cache coverage, output device routing, provider readiness, and
  configured profile triggers.
- [x] **SAY-02**: User can see say-path latency from trigger/hotkey to playback
  start for cached responses.
- [x] **SAY-03**: User can force prepared playback without waiting for trigger
  detection and receive a clear reason if playback is blocked.
- [x] **SAY-04**: User can keep auto-mode responsive when response-cache lookup
  misses by using a documented prepared-response fallback.

### Training Loop

- [x] **TRAIN-01**: User can list captured sample folders and inspect metadata
  without opening raw JSON files manually.
- [x] **TRAIN-02**: User can replay selected captured samples through a local
  command to validate transcripts and classifications.
- [x] **TRAIN-03**: User can export a sanitized evaluation report that excludes
  raw audio and private config values.

## v1.1 Requirements

Requirements for milestone v1.1 Call Intelligence Loop.

### Speaker-Aware Samples

- [x] **SPK-01**: User can attach and read local speaker labels for captured
  trigger samples from sidecar metadata without requiring cloud diarization.
- [x] **SPK-02**: User can run trigger evaluation grouped by speaker label and
  see answer decisions for `me`, `other`, and `unknown` speakers separately.
- [x] **SPK-03**: User can set or correct a sample's speaker label from the CLI
  and keep the update local to the sample metadata.

### Local Trigger Classifier

- [x] **CLF-01**: User can mark a sample's answer decision as accepted or
  rejected from the CLI without editing JSON manually.
- [x] **CLF-02**: User can train a lightweight local trigger classifier from
  accepted/rejected samples after seeing a data-sufficiency check.
- [x] **CLF-03**: User can run the classifier in shadow mode during
  `trigger-eval` and `trigger-check`, comparing learned confidence against the
  deterministic trigger/addressing gate before enabling it.

### Provider Latency

- [ ] **LAT-01**: User can run a provider-specific latency probe against an
  active Chrome call using the existing provider abstraction.
- [ ] **LAT-02**: User can see end-to-end latency segments for capture,
  transcription, trigger decision, provider unmute, playback start, and mute
  recovery.
- [ ] **LAT-03**: User can export latency run history by profile and provider
  to identify recurring bottlenecks.

## Future Requirements

Deferred beyond v1.1.

### Advanced Automation

- User can install and run a fully local diarization engine as a first-class
  Saymo component.
- User can enable the trained classifier in live auto-mode after enough
  validated shadow-mode evidence.
- User can run provider-specific UI regression checks when call-provider web
  apps change their controls.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Required cloud transcription | Violates local-by-default privacy constraint |
| Voice-clone training from call recordings | This milestone is about trigger behavior, not voice identity |
| Fully autonomous meeting agent | Manual takeover and explicit prepared playback remain required safety paths |
| Provider UI redesign | This is CLI/control-path work; provider automation stays behind existing abstractions |
| Required diarization dependency | v1.1 must work with sidecar labels even when no diarization engine is installed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CATCH-01 | Phase 1 | Complete |
| SAY-02 | Phase 1 | Complete |
| CATCH-02 | Phase 2 | Complete |
| CATCH-03 | Phase 2 | Complete |
| CATCH-04 | Phase 2 | Complete |
| SAY-01 | Phase 3 | Complete |
| SAY-03 | Phase 3 | Complete |
| SAY-04 | Phase 3 | Complete |
| TRAIN-01 | Phase 4 | Complete |
| TRAIN-02 | Phase 4 | Complete |
| TRAIN-03 | Phase 4 | Complete |
| SPK-01 | Phase 5 | Complete |
| SPK-02 | Phase 5 | Complete |
| SPK-03 | Phase 5 | Complete |
| CLF-01 | Phase 6 | Complete |
| CLF-02 | Phase 6 | Complete |
| CLF-03 | Phase 6 | Complete |
| LAT-01 | Phase 7 | Pending |
| LAT-02 | Phase 7 | Pending |
| LAT-03 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 11 total
- v1.1 requirements: 9 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-05-15*
*Last updated: 2026-05-18 after completing Phase 6*
