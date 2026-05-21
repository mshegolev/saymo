# Roadmap: Saymo

## Overview

Milestone v1.5 focuses on Live Review + Safe Approved Speak: using real
captured-call evidence to reduce false handoffs, bootstrap speaker labels,
close the approved-draft playback loop, and make saved sessions reusable as
regression fixtures.

## Completed Milestones

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
  Archive: `.planning/milestones/v1.2-ROADMAP.md`
- ✅ **v1.1 Call Intelligence Loop** - Phases 5-7 shipped 2026-05-18.
  Archive: `.planning/milestones/v1.1-ROADMAP.md`
- ✅ **v1.0 Speedly Catcher + Speedly Sayer** - Phases 1-4 shipped
  2026-05-15.

## Active Milestone

- **v1.5 Live Review + Safe Approved Speak** - Phases 18-22 planned.

## Phases

**Phase Numbering:**
- Integer phases (18, 19, 20, 21, 22): Planned milestone work
- Decimal phases (19.1, 19.2): Urgent insertions if needed

- [x] **Phase 18: Post-call Review Queue** - Prioritize real-session samples
  that most affect handoff, speaker, and classifier quality.
- [ ] **Phase 19: Addressing v2** - Separate direct handoffs from incidental
  name mentions and explain the decision path.
- [ ] **Phase 20: Speaker Bootstrap** - Reduce unknown-speaker coverage for
  completed sessions without requiring live diarization.
- [ ] **Phase 21: Approved Draft Playback** - Play only explicitly approved
  generated drafts through existing safe TTS/playback paths.
- [ ] **Phase 22: Regression Replay** - Re-run saved sessions through current
  logic and report reliability metrics.

## Phase Details

### Phase 18: Post-call Review Queue
**Goal**: Let the user review the highest-value samples from one completed
session first and apply labels needed for safer live behavior.
**Depends on**: v1.2 review commands, v1.4 meeting memory
**Requirements**: REV-05, REV-06, REV-07
**Success Criteria** (what must be TRUE):
  1. A user can open a session-scoped review queue that ranks likely handoffs,
     questions, name mentions, unknown speakers, and classifier-critical
     samples ahead of ordinary speech.
  2. A user can apply category, speaker, and answer-decision labels from the
     queue without editing JSON directly.
  3. The queue reports remaining unknown speakers, unlabeled decisions,
     accepted/rejected counts, and classifier-readiness blockers.
  4. Existing `trigger-samples review/list/category/decision/label` flows still
     work for manual review.
**Plans**: 4 plans

Plans:
- [x] 18-01: Add post-call review priority scoring and queue model
- [x] 18-02: Add session-scoped review command and batch-safe label actions
- [x] 18-03: Add review progress and classifier-readiness diagnostics
- [x] 18-04: Add docs, edge-case tests, and no-raw-audio report checks

### Phase 19: Addressing v2
**Goal**: Stop treating every recognized name as an addressed-to-me handoff
while keeping true handoff detection explainable and tunable.
**Depends on**: Phase 18
**Requirements**: INT-02, INT-03, INT-04, INT-05
**Success Criteria** (what must be TRUE):
  1. Incidental first-name and full-name/surname mentions can be classified as
     mention-only instead of `addressed_to_me`.
  2. Direct handoffs such as "John, what do you think?" still produce an
     answer candidate or confirmation wait.
  3. `trigger-check` explains matched phrase, local context, decision path,
     final action, and skip/answer reason.
  4. Per-profile config can tune handoff and mention-only patterns without
     hardcoded private names in source.
  5. Saved false-positive and true-handoff samples can be replayed against
     Addressing v2.
**Plans**: 4 plans

Plans:
- [ ] 19-01: Add addressing evidence model and explainable decision output
- [ ] 19-02: Add direct-handoff vs mention-only heuristics
- [ ] 19-03: Add profile-configured handoff and mention-pattern tuning
- [ ] 19-04: Add saved-sample replay tests for false positives and true handoffs

### Phase 20: Speaker Bootstrap
**Goal**: Turn completed sessions with `speaker=unknown` into usable
speaker-labeled training evidence through reviewed local workflows.
**Depends on**: Phase 18, v1.3 diarization sidecars
**Requirements**: SPKR-04, SPKR-05, QUAL-04
**Success Criteria** (what must be TRUE):
  1. A user can bootstrap speaker labels for one completed session from
     reviewed diarization suggestions or a lightweight manual grouping flow.
  2. Bulk label application preserves manual labels as authoritative and keeps
     suggestion/audit metadata inspectable.
  3. Session output reports `me`, `other`, and `unknown` counts by category and
     shows classifier-readiness impact.
  4. Saymo remains usable when diarization is disabled or unavailable.
**Plans**: 3 plans

Plans:
- [ ] 20-01: Add speaker bootstrap candidates from sessions and suggestions
- [ ] 20-02: Add bulk speaker label apply flow with audit preservation
- [ ] 20-03: Add speaker coverage/readiness reports and disabled-backend tests

### Phase 21: Approved Draft Playback
**Goal**: Let the user send only explicitly approved generated draft text into
the live call through existing local TTS and playback safety paths.
**Depends on**: v1.4 answer cockpit, existing TTS/playback routing
**Requirements**: COCK-03, COCK-04, AUD-03, SAFE-01
**Success Criteria** (what must be TRUE):
  1. `answer-cockpit action --action speak` can route an approved draft through
     configured local TTS and playback devices.
  2. Unapproved generated draft text is refused before synthesis or playback.
  3. A user can preview/monitor, cancel, or timeout approved draft playback.
  4. Audit events record draft id, action id, TTS engine, output route,
     playback start/end, cancellation, and blocked reasons.
  5. Manual takeover, confirmation, and max-duration safety behavior remains
     intact.
**Plans**: 4 plans

Plans:
- [ ] 21-01: Add approved playback request model and blocked-reason gates
- [ ] 21-02: Wire approved drafts into existing TTS and playback routing
- [ ] 21-03: Add preview, monitor, cancel, timeout, and max-duration controls
- [ ] 21-04: Extend audit/reporting and safety regression tests

### Phase 22: Regression Replay
**Goal**: Make saved sessions reusable as a local reliability test for
addressing, question detection, speaker coverage, and live-assist readiness.
**Depends on**: Phases 18-21
**Requirements**: REG-01, REG-02, REG-03
**Success Criteria** (what must be TRUE):
  1. A user can replay one saved capture session through current addressing,
     question, speaker, and classifier logic without re-recording audio.
  2. Regression output reports false handoffs, missed handoffs, question noise,
     speaker coverage, review coverage, and live-assist readiness.
  3. A user can compare before/after results and export a sanitized report.
  4. Regression reports omit raw audio and secrets and avoid committing local
     transcripts or recordings.
**Plans**: 3 plans

Plans:
- [ ] 22-01: Add saved-session replay engine over local sample metadata
- [ ] 22-02: Add reliability metrics and before/after comparison
- [ ] 22-03: Add sanitized regression reports, docs, and fixture tests

## Progress

**Execution Order:**
Phases execute in numeric order: 18 -> 19 -> 20 -> 21 -> 22

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 18. Post-call Review Queue | v1.5 | 4/4 | Complete | 2026-05-21 |
| 19. Addressing v2 | v1.5 | 0/4 | Pending | — |
| 20. Speaker Bootstrap | v1.5 | 0/3 | Pending | — |
| 21. Approved Draft Playback | v1.5 | 0/4 | Pending | — |
| 22. Regression Replay | v1.5 | 0/3 | Pending | — |

## Requirement Coverage

| Requirement | Phase |
|-------------|-------|
| REV-05 | Phase 18 |
| REV-06 | Phase 18 |
| REV-07 | Phase 18 |
| INT-02 | Phase 19 |
| INT-03 | Phase 19 |
| INT-04 | Phase 19 |
| INT-05 | Phase 19 |
| SPKR-04 | Phase 20 |
| SPKR-05 | Phase 20 |
| QUAL-04 | Phase 20 |
| COCK-03 | Phase 21 |
| COCK-04 | Phase 21 |
| AUD-03 | Phase 21 |
| SAFE-01 | Phase 21 |
| REG-01 | Phase 22 |
| REG-02 | Phase 22 |
| REG-03 | Phase 22 |

**Coverage:** 17/17 requirements mapped.
