# Roadmap: Saymo

## Overview

Milestone v1.2 focuses on the Trigger Training Console: turning recorded
call samples into a practical local loop for session review, relabeling, and
safe classifier promotion.

## Completed Milestones

- ✅ **v1.0 Speedly Catcher + Speedly Sayer** - Phases 1-4 complete.
- ✅ **v1.1 Call Intelligence Loop** - Phases 5-7 complete.
  Archive: `.planning/milestones/v1.1-ROADMAP.md`

## Active Milestone

- 🚧 **v1.2 Trigger Training Console** - Phases 8-10 planned.

## Phases

**Phase Numbering:**
- Integer phases (8, 9, 10): Planned milestone work
- Decimal phases (9.1, 9.2): Urgent insertions

- [ ] **Phase 8: Capture Session Ledger** - Track named trigger-capture
  sessions and summarize what each recording run saved.
- [ ] **Phase 9: Review And Relabel Workflow** - Let the user filter, replay,
  and correct sample category/speaker/answer labels without JSON edits.
- [ ] **Phase 10: Classifier Readiness Gate** - Add local quality/readiness
  checks and guarded per-profile live-assist configuration.

## Phase Details

### Phase 8: Capture Session Ledger
**Goal**: Treat each recording run as a named local session with auditable
counts and metadata.
**Depends on**: v1.1 trigger sample metadata and capture command
**Requirements**: SES-01, SES-02, SES-03
**Success Criteria** (what must be TRUE):
  1. Starting trigger capture with a session id stores that id in every sample.
  2. A completed session summary reports counts by category, speaker, decision,
     and skipped silence.
  3. Prior sessions can be listed by profile with timestamps and sample counts.
  4. Existing samples without session ids remain valid.
**Plans**: 3 plans

Plans:
- [ ] 08-01: Add session metadata and storage helpers
- [ ] 08-02: Wire session ids into trigger-capture
- [ ] 08-03: Add session list/summary commands and docs

### Phase 9: Review And Relabel Workflow
**Goal**: Make saved samples easy to triage and correct from the CLI after a
call.
**Depends on**: Phase 8
**Requirements**: REV-01, REV-02, REV-03, REV-04
**Success Criteria** (what must be TRUE):
  1. Sample listing supports profile, session, category, speaker, decision,
     disagreement, and date filters.
  2. Category correction writes consistent metadata and keeps the adjacent WAV
     discoverable.
  3. Review queue can replay samples and write category/speaker/decision labels
     in one command flow.
  4. Sanitized review reports group results by session and category without raw
     audio payloads.
**Plans**: 4 plans

Plans:
- [ ] 09-01: Extend sample filtering and disagreement detection
- [ ] 09-02: Add category relabel command
- [ ] 09-03: Add interactive review queue
- [ ] 09-04: Add session-aware sanitized reports and docs

### Phase 10: Classifier Readiness Gate
**Goal**: Let learned behavior assist live calls only when local evidence is
strong enough and deterministic safety checks still pass.
**Depends on**: Phase 9
**Requirements**: CLS-01, CLS-02, CLS-03, CLS-04
**Success Criteria** (what must be TRUE):
  1. Readiness check reports label balance, category coverage,
     mention-vs-handoff coverage, and threshold failures.
  2. Holdout evaluation reports answer/skip quality metrics from local samples.
  3. Per-profile live-assist config cannot be enabled until readiness passes.
  4. Live-assist diagnostics explain classifier confidence and feature signals
     without cloud calls.
**Plans**: 4 plans

Plans:
- [ ] 10-01: Add classifier readiness metrics
- [ ] 10-02: Add holdout evaluation reporting
- [ ] 10-03: Add guarded per-profile live-assist config
- [ ] 10-04: Add live-assist diagnostics and docs

## Progress

**Execution Order:**
Phases execute in numeric order: 8 → 9 → 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 8. Capture Session Ledger | v1.2 | 0/3 | Planned | — |
| 9. Review And Relabel Workflow | v1.2 | 0/4 | Planned | — |
| 10. Classifier Readiness Gate | v1.2 | 0/4 | Planned | — |
