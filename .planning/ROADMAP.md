# Roadmap: Saymo

## Overview

Milestone v1.3 focuses on Local Diarization Assist: making local speaker
identity useful for trigger training without making diarization a required
runtime dependency or adding risky real-time behavior to `saymo auto`.

## Completed Milestones

- ✅ **v1.0 Speedly Catcher + Speedly Sayer** - Phases 1-4 shipped
  2026-05-15.
- ✅ **v1.1 Call Intelligence Loop** - Phases 5-7 shipped 2026-05-18.
  Archive: `.planning/milestones/v1.1-ROADMAP.md`
- ✅ **v1.2 Trigger Training Console** - Phases 8-10 shipped 2026-05-20.
  Archive: `.planning/milestones/v1.2-ROADMAP.md`

## Active Milestone

- **v1.3 Local Diarization Assist** - Phases 11-13 planned.

## Phases

**Phase Numbering:**
- Integer phases (11, 12, 13): Planned milestone work
- Decimal phases (12.1, 12.2): Urgent insertions if needed

- [x] **Phase 11: Diarization Adapter And Config** - Add optional local
  diarization backend detection, configuration, and stable data contracts.
- [x] **Phase 12: Session Speaker Suggestions** - Run diarization against
  completed capture sessions and store reviewable speaker suggestions.
- [ ] **Phase 13: Speaker Review And Quality Reports** - Promote reviewed
  suggestions into sample labels and report speaker-label quality before
  training.

## Phase Details

### Phase 11: Diarization Adapter And Config
**Goal**: Let Saymo detect and configure optional local diarization backends
without adding a required ML dependency.
**Depends on**: v1.2 capture sessions and speaker labels
**Requirements**: DIAR-01, DIAR-02, DIAR-03
**Success Criteria** (what must be TRUE):
  1. A user can check diarization availability and see missing dependency or
     model/token guidance without crashing.
  2. Diarization config supports disabled-by-default local engines, model id,
     device, speaker count bounds, and env-var secrets.
  3. A shared adapter contract can represent speaker segments and confidence
     without importing optional backend packages at module import time.
  4. Default Saymo install and existing tests remain usable without diarization
     dependencies.
**Plans**: 3 plans

Plans:
- [ ] 11-01: Add diarization config and backend availability checks
- [ ] 11-02: Add backend-neutral diarization result contracts
- [ ] 11-03: Add CLI diagnostics and docs for optional setup

### Phase 12: Session Speaker Suggestions
**Goal**: Run local diarization over completed trigger-capture sessions and
store reviewable speaker suggestions beside existing sample metadata.
**Depends on**: Phase 11
**Requirements**: DIAR-04, SPKR-01, SPKR-02
**Success Criteria** (what must be TRUE):
  1. A user can diarize one completed capture session by profile/session id.
  2. Saymo writes local sidecar metadata for diarization segments and per-sample
     speaker suggestions without overwriting manual `speaker` labels.
  3. Session output reports speaker cluster ids, time ranges, sample counts,
     confidence, and unresolved/unknown coverage.
  4. Existing review/list/report commands keep working for sessions with no
     diarization sidecars.
**Plans**: 3 plans

Plans:
- [ ] 12-01: Load session audio windows and run diarization backend
- [ ] 12-02: Store diarization sidecars and sample speaker suggestions
- [ ] 12-03: Add session speaker-summary command output

### Phase 13: Speaker Review And Quality Reports
**Goal**: Let the user inspect, accept, and measure speaker suggestions before
they affect classifier readiness or training.
**Depends on**: Phase 12
**Requirements**: SPKR-03, QUAL-01, QUAL-02, QUAL-03
**Success Criteria** (what must be TRUE):
  1. Review flows can show suggested speaker labels and apply accepted
     suggestions to the existing `speaker` metadata field.
  2. Manual labels remain authoritative and suggestion conflicts are preserved
     for audit.
  3. Speaker quality reports show unknown coverage, accepted suggestion counts,
     confidence buckets, and manual-vs-suggested conflicts by session.
  4. Trigger evaluation/readiness can distinguish manual labels from unaccepted
     suggestions and does not silently train on unreviewed speaker guesses.
**Plans**: 4 plans

Plans:
- [ ] 13-01: Extend sample review with speaker suggestions
- [ ] 13-02: Add speaker suggestion apply/reject metadata
- [ ] 13-03: Add speaker quality and conflict reports
- [ ] 13-04: Wire reviewed labels into evaluation/readiness docs and tests

## Progress

**Execution Order:**
Phases execute in numeric order: 11 -> 12 -> 13

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 11. Diarization Adapter And Config | v1.3 | 3/3 | Complete | 2026-05-20 |
| 12. Session Speaker Suggestions | v1.3 | 3/3 | Complete | 2026-05-20 |
| 13. Speaker Review And Quality Reports | v1.3 | 0/4 | Not started | - |
