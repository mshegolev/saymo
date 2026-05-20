# Requirements: Saymo

**Defined:** 2026-05-20
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.3 Requirements

Requirements for milestone v1.3 Local Diarization Assist.

### Optional Diarization

- [x] **DIAR-01**: User can check whether a configured local diarization backend
  is available and see actionable setup diagnostics when it is missing.
- [x] **DIAR-02**: User can configure diarization engine, model id, device,
  speaker-count bounds, and required tokens through config/env without
  committing secrets.
- [x] **DIAR-03**: User can keep Saymo fully usable when diarization is disabled
  or dependencies are not installed.
- [x] **DIAR-04**: User can run diarization against one completed
  trigger-capture session and store the output locally.

### Speaker Mapping

- [x] **SPKR-01**: User can inspect diarization speaker clusters for a session,
  including cluster id, time range, sample count, confidence, and unknown
  coverage.
- [x] **SPKR-02**: User can map diarization speaker ids to Saymo labels
  `me`, `other`, or `unknown` for the current profile/session.
- [ ] **SPKR-03**: User can review, accept, reject, or override suggested
  speaker labels without losing the original diarization suggestion.

### Training Signal Quality

- [ ] **QUAL-01**: User can report speaker-label quality by session, including
  unknown coverage, accepted suggestion count, confidence buckets, and
  manual-vs-suggested conflicts.
- [ ] **QUAL-02**: User can run trigger evaluation/readiness with manual speaker
  labels taking precedence over unreviewed suggestions.
- [ ] **QUAL-03**: User can export sanitized diarization/speaker-review reports
  without raw audio payloads, transcript text, or private config values.

## Future Requirements

Deferred beyond v1.3.

### Live Speaker Context

- User can use validated speaker identity hints during live auto-mode without
  increasing false positives or adding unacceptable latency.
- User can compare real-time speaker hints against post-call diarization
  results.

### Provider UI Regression

- User can run provider-specific UI regression checks when Chrome call-provider
  controls change.
- User can record provider automation failures as reproducible diagnostics.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Required diarization dependency in the base install | Saymo must remain lightweight and local-by-default when diarization is unused. |
| Cloud diarization as the default path | Meeting audio should not leave the machine by default. |
| Real-time diarization inside `saymo auto` | Latency and safety risk are too high before offline session suggestions are validated. |
| Automatic overwrite of manual speaker labels | Manual review remains authoritative for training data. |
| Provider UI regression checks | Useful but separate from speaker identity and deferred beyond v1.3. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DIAR-01 | Phase 11 | Complete |
| DIAR-02 | Phase 11 | Complete |
| DIAR-03 | Phase 11 | Complete |
| DIAR-04 | Phase 12 | Complete |
| SPKR-01 | Phase 12 | Complete |
| SPKR-02 | Phase 12 | Complete |
| SPKR-03 | Phase 13 | Pending |
| QUAL-01 | Phase 13 | Pending |
| QUAL-02 | Phase 13 | Pending |
| QUAL-03 | Phase 13 | Pending |

**Coverage:**
- v1.3 requirements: 10 total
- Mapped to phases: 10
- Complete: 6
- Unmapped: 0

---
*Requirements defined: 2026-05-20*
*Last updated: 2026-05-20 after completing Phase 12*
