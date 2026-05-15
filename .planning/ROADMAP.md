# Roadmap: Saymo

## Overview

Milestone v1.0 makes Saymo's live-call path faster and easier to tune. The
roadmap first adds timing visibility, then turns captured samples into an
offline catch-evaluation loop, then hardens the say/preflight path, and finally
wraps the sample workflow in operator-facing commands and docs.

## Milestones

- ✅ **v1.0 Speedly Catcher + Speedly Sayer** - Phases 1-4 (complete)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions

- [x] **Phase 1: Latency Baseline** - Measure catch and say latency without
  changing behavior.
- [x] **Phase 2: Catcher Tuning Loop** - Add profile tuning and offline sample
  evaluation.
- [x] **Phase 3: Sayer Preflight Path** - Verify readiness and speed up
  prepared playback decisions.
- [x] **Phase 4: Sample Review Workflow** - Make captured samples inspectable,
  replayable, and reportable.

## Phase Details

### Phase 1: Latency Baseline
**Goal**: Add trustworthy timing around live windows and playback start so
future speed work is measured, not guessed.
**Depends on**: Nothing
**Requirements**: CATCH-01, SAY-02
**Success Criteria** (what must be TRUE):
  1. User can run auto/diagnostic paths and see catch timing split by capture,
     transcription, trigger match, addressing, and action.
  2. User can trigger cached playback and see time-to-playback-start.
  3. Existing trigger gating behavior remains unchanged under the new metrics.
**Plans**: 2 plans

Plans:
- [x] 01-01: Instrument catch-path timings
- [x] 01-02: Instrument say-path playback timings

### Phase 2: Catcher Tuning Loop
**Goal**: Let the user tune live detection from config and validate changes
against saved call samples.
**Depends on**: Phase 1
**Requirements**: CATCH-02, CATCH-03, CATCH-04
**Success Criteria** (what must be TRUE):
  1. User can configure per-profile window, overlap, cooldown, and silence
     behavior without source edits.
  2. User can run offline evaluation over `~/.saymo/trigger_samples/<profile>/`
     and see categorized results plus suspected misses/false positives.
  3. User can promote a heard variant from an evaluated sample and re-run the
     same evaluation with changed results.
**Plans**: 3 plans

Plans:
- [x] 02-01: Add profile-level catcher tuning config
- [x] 02-02: Build offline trigger-sample evaluator
- [x] 02-03: Add promote-and-rerun workflow for fuzzy variants

### Phase 3: Sayer Preflight Path
**Goal**: Make prepared-response playback readiness explicit before calls and
keep auto-mode responsive when playback cannot start.
**Depends on**: Phase 2
**Requirements**: SAY-01, SAY-03, SAY-04
**Success Criteria** (what must be TRUE):
  1. User can run one preflight command that checks cache, devices, provider,
     triggers, and response fallback status.
  2. User can force prepared playback and get a precise blocked reason when it
     cannot play.
  3. Auto-mode remains listening after a cache miss or blocked playback path.
**Plans**: 3 plans

Plans:
- [x] 03-01: Add live-call preflight command
- [x] 03-02: Normalize forced-playback blocked reasons
- [x] 03-03: Harden cache-miss fallback behavior

### Phase 4: Sample Review Workflow
**Goal**: Turn captured call windows into a practical local review loop for
training and debugging trigger behavior.
**Depends on**: Phase 3
**Requirements**: TRAIN-01, TRAIN-02, TRAIN-03
**Success Criteria** (what must be TRUE):
  1. User can list captured samples by profile/category with transcript,
     trigger, question, and level metadata.
  2. User can replay a selected sample locally and compare transcript,
     classification, and detector action.
  3. User can export a sanitized report without raw audio or private config
     values.
**Plans**: 3 plans

Plans:
- [x] 04-01: Add sample listing command
- [x] 04-02: Add sample replay and reclassify command
- [x] 04-03: Add sanitized evaluation report and docs

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Latency Baseline | v1.0 | 2/2 | Complete | 2026-05-15 |
| 2. Catcher Tuning Loop | v1.0 | 3/3 | Complete | 2026-05-15 |
| 3. Sayer Preflight Path | v1.0 | 3/3 | Complete | 2026-05-15 |
| 4. Sample Review Workflow | v1.0 | 3/3 | Complete | 2026-05-15 |
