# Requirements: Saymo

**Defined:** 2026-05-20
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.2 Requirements

Requirements for milestone v1.2 Trigger Training Console.

### Capture Sessions

- [x] **SES-01**: User can start a named trigger-capture session and have every
  saved sample record the session id in its JSON metadata.
- [x] **SES-02**: User can stop or finish a session and see a local summary of
  sample counts by category, speaker, answer decision, and silence/skipped
  windows.
- [x] **SES-03**: User can list prior capture sessions for a profile and inspect
  their time range, sample counts, and training-readiness status.

### Review And Relabel

- [ ] **REV-01**: User can filter saved samples by profile, session, category,
  speaker, answer decision, current classifier disagreement, and date range.
- [ ] **REV-02**: User can correct a sample category from the CLI, including
  `asked_to_speak`, `mentioned_me`, `question`, `speech`, and `silence`,
  without manually editing JSON.
- [ ] **REV-03**: User can run a review queue that replays samples one by one
  and accepts category, speaker, and answer-decision corrections from one
  command flow.
- [ ] **REV-04**: User can export a sanitized training-review report grouped by
  session and category, without raw audio payloads or private config values.

### Classifier Readiness

- [ ] **CLS-01**: User can run a readiness check that reports accepted/rejected
  label balance, category coverage, mention-vs-handoff coverage, and minimum
  sample thresholds per profile.
- [ ] **CLS-02**: User can run a local holdout evaluation for the trained
  classifier and see precision/recall-style quality metrics for answer vs skip.
- [ ] **CLS-03**: User can configure classifier live-assist mode per profile,
  but only after readiness gates pass; deterministic trigger/addressing checks
  remain the hard safety boundary.
- [ ] **CLS-04**: User can inspect why classifier live-assist accepted or
  rejected a candidate answer using local features and confidence, with no
  cloud calls.

## Future Requirements

Deferred beyond v1.2.

### Optional Diarization

- User can install and run a fully local diarization engine as a first-class
  Saymo component.
- User can auto-suggest speaker labels from local diarization while preserving
  manual override.

### Provider UI Regression

- User can run provider-specific UI regression checks when Chrome call-provider
  controls change.
- User can record provider automation failures as reproducible diagnostics.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Required cloud diarization | Violates local-by-default operation and is not needed for manual review. |
| Training voice-clone models from call recordings | This milestone is about trigger decisions, not voice identity. |
| Fully autonomous meeting participation | Manual takeover and deterministic gating remain safety boundaries. |
| Replacing deterministic trigger checks with ML | v1.2 may add live assist, but deterministic checks stay authoritative. |
| Provider UI redesign | Provider automation hardening is separate from sample training workflow. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SES-01 | Phase 8 | Complete |
| SES-02 | Phase 8 | Complete |
| SES-03 | Phase 8 | Complete |
| REV-01 | Phase 9 | Pending |
| REV-02 | Phase 9 | Pending |
| REV-03 | Phase 9 | Pending |
| REV-04 | Phase 9 | Pending |
| CLS-01 | Phase 10 | Pending |
| CLS-02 | Phase 10 | Pending |
| CLS-03 | Phase 10 | Pending |
| CLS-04 | Phase 10 | Pending |

**Coverage:**
- v1.2 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-05-20*
*Last updated: 2026-05-20 after starting milestone v1.2*
