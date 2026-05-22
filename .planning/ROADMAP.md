# Roadmap: Saymo

## Overview

Milestone v1.7 focuses on Live Reliability Rehearsal: proving the local live
loop before and after real calls with guided rehearsal, session scorecards,
remediation hints, and a repeatable safety soak gate.

## Completed Milestones

- ✅ **v1.6 Live Control Handbrake** - Phases 23-26 shipped 2026-05-22.
  Archives: `.planning/milestones/v1.6-ROADMAP.md`,
  `.planning/milestones/v1.6-REQUIREMENTS.md`,
  `.planning/milestones/v1.6-MILESTONE-AUDIT.md`,
  `.planning/milestones/v1.6-phases/`
- ✅ **v1.5 Live Review + Safe Approved Speak** - Phases 18-22 shipped
  2026-05-21.
  Archives: `.planning/milestones/v1.5-ROADMAP.md`,
  `.planning/milestones/v1.5-REQUIREMENTS.md`,
  `.planning/milestones/v1.5-MILESTONE-AUDIT.md`,
  `.planning/milestones/v1.5-phases/`
- ✅ **v1.4 Live Conversation Memory + Answer Cockpit** - Phases 14-17 shipped
  2026-05-20.
  Archives: `.planning/milestones/v1.4-ROADMAP.md`,
  `.planning/milestones/v1.4-REQUIREMENTS.md`,
  `.planning/milestones/v1.4-MILESTONE-AUDIT.md`
- ✅ **v1.3 Local Diarization Assist** - Phases 11-13 shipped 2026-05-20.
  Archives: `.planning/milestones/v1.3-ROADMAP.md`,
  `.planning/milestones/v1.3-REQUIREMENTS.md`,
  `.planning/milestones/v1.3-MILESTONE-AUDIT.md`
- ✅ **v1.2 Trigger Training Console** - Phases 8-10 shipped 2026-05-20.
  Archives: `.planning/milestones/v1.2-ROADMAP.md`,
  `.planning/milestones/v1.2-REQUIREMENTS.md`,
  `.planning/milestones/v1.2-MILESTONE-AUDIT.md`
- ✅ **v1.1 Call Intelligence Loop** - Phases 5-7 shipped 2026-05-18.
  Archives: `.planning/milestones/v1.1-ROADMAP.md`,
  `.planning/milestones/v1.1-REQUIREMENTS.md`
- ✅ **v1.0 Speedly Catcher + Speedly Sayer** - Phases 1-4 shipped
  2026-05-15.

## Active Milestone

- **v1.7 Live Reliability Rehearsal** - Phases 27-30 planned.

## Phases

**Phase Numbering:**
- Integer phases (27, 28, 29, 30): Planned milestone work
- Decimal phases (28.1, 28.2): Urgent insertions if needed

- [ ] **Phase 27: Pre-call Rehearsal Runner** - Add a guided local rehearsal
  path that checks the full live loop before joining a real meeting.
- [ ] **Phase 28: Session Reliability Scorecard** - Summarize reliability for
  real and rehearsal sessions with sanitized evidence.
- [ ] **Phase 29: Remediation Advisor** - Turn failed readiness and reliability
  checks into concrete next actions.
- [ ] **Phase 30: Safety Soak Regression Gate** - Run saved sessions and
  rehearsals as a repeatable safety gate.

## Phase Details

### Phase 27: Pre-call Rehearsal Runner
**Goal**: Let the user exercise Saymo's capture, trigger, handbrake, and
playback safety path before a real call.
**Depends on**: v1.6 live-control state, `auto-preflight`, `hotkey-doctor`,
trigger replay, approved playback gates
**Requirements**: REH-01, REH-02, REH-03, REH-04
**Success Criteria** (what must be TRUE):
  1. User can run one rehearsal command for a profile without joining a real
     meeting.
  2. Rehearsal dry-run reports would-speak and would-block decisions without
     sending audio into the call output.
  3. Rehearsal writes a local artifact compatible with later scorecards and
     replay.
  4. Rehearsal summary reports pass/warn/fail with exact blocking reasons.
**Plans**: 4 plans

Plans:
- [ ] 27-01: Define rehearsal artifact model and local storage
- [ ] 27-02: Add profile-scoped rehearsal command and dry-run path
- [ ] 27-03: Exercise trigger, handbrake, hotkey, and playback gate checks
- [ ] 27-04: Add rehearsal summary output and tests

### Phase 28: Session Reliability Scorecard
**Goal**: Give the user one sanitized reliability report for a real or
rehearsal session.
**Depends on**: Phase 27, v1.5 regression replay, v1.6 handbrake audit
**Requirements**: REL-01, REL-02, REL-03, REL-04
**Success Criteria** (what must be TRUE):
  1. User can generate a scorecard for a saved capture session or rehearsal
     artifact.
  2. Scorecard reports trigger, addressing, question, speaker, and classifier
     readiness metrics.
  3. Scorecard reports playback, handbrake, latency, cancellation, and blocked
     automatic speaking evidence.
  4. Markdown/JSON exports are sanitized by default.
**Plans**: 4 plans

Plans:
- [ ] 28-01: Add scorecard data model and session loaders
- [ ] 28-02: Add trigger/addressing/speaker reliability metrics
- [ ] 28-03: Add playback, handbrake, latency, and safety metrics
- [ ] 28-04: Add sanitized Markdown/JSON export and tests

### Phase 29: Remediation Advisor
**Goal**: Convert failed checks into concrete user actions instead of leaving
the user to interpret raw diagnostics.
**Depends on**: Phases 27-28, `auto-preflight`, `hotkey-doctor`,
`takeover-check`
**Requirements**: FIX-01, FIX-02, FIX-03
**Success Criteria** (what must be TRUE):
  1. User sees actionable remediation hints for failed rehearsal, scorecard,
     hotkey, preflight, and takeover checks.
  2. Each hint classifies the next action as config, macOS permission, audio
     routing, source data, review labeling, or retest.
  3. User can rerun the affected check without rerunning the whole workflow.
**Plans**: 3 plans

Plans:
- [ ] 29-01: Add remediation taxonomy and hint renderer
- [ ] 29-02: Wire hints into rehearsal, scorecard, and doctor/preflight checks
- [ ] 29-03: Add targeted rerun commands and remediation tests

### Phase 30: Safety Soak Regression Gate
**Goal**: Make saved sessions and rehearsals a repeatable gate before merge or
before trusting Saymo in another meeting.
**Depends on**: Phases 27-29
**Requirements**: SOAK-01, SOAK-02, SOAK-03, SOAK-04
**Success Criteria** (what must be TRUE):
  1. User can run a safety soak command for one profile.
  2. Soak fails if automatic speaking happens while handbrake state forbids it
     or while a generated draft is unapproved.
  3. Soak compares reliability drift against a prior baseline.
  4. Soak emits one pass/fail summary with links to scorecard and remediation
     output.
**Plans**: 4 plans

Plans:
- [ ] 30-01: Add soak runner over saved rehearsal and session artifacts
- [ ] 30-02: Add safety invariants for handbrake and approval gates
- [ ] 30-03: Add baseline comparison for reliability drift
- [ ] 30-04: Add single-command gate output, docs, and tests

## Progress

**Execution Order:**
Phases execute in numeric order: 27 -> 28 -> 29 -> 30

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 27. Pre-call Rehearsal Runner | v1.7 | 0/4 | Pending | - |
| 28. Session Reliability Scorecard | v1.7 | 0/4 | Pending | - |
| 29. Remediation Advisor | v1.7 | 0/3 | Pending | - |
| 30. Safety Soak Regression Gate | v1.7 | 0/4 | Pending | - |

## Requirement Coverage

| Requirement | Phase |
|-------------|-------|
| REH-01 | Phase 27 |
| REH-02 | Phase 27 |
| REH-03 | Phase 27 |
| REH-04 | Phase 27 |
| REL-01 | Phase 28 |
| REL-02 | Phase 28 |
| REL-03 | Phase 28 |
| REL-04 | Phase 28 |
| FIX-01 | Phase 29 |
| FIX-02 | Phase 29 |
| FIX-03 | Phase 29 |
| SOAK-01 | Phase 30 |
| SOAK-02 | Phase 30 |
| SOAK-03 | Phase 30 |
| SOAK-04 | Phase 30 |

**Coverage:** 15/15 requirements mapped.
