# Roadmap: Saymo v1.13 F5 Prosody Metrics

## Overview

v1.13 makes F5 voice timing comparisons more objective and context-aware. The
work starts by expanding sanitized preview coverage, then adds measurable
speech-rate and pause-distribution comparisons, and finishes by routing pause
presets by answer source while preserving profile defaults and cache safety.

## Phases

**Phase Numbering:**
- Integer phases (45, 46, 47): Planned v1.13 milestone work
- Decimal phases (45.1, 45.2): Urgent insertions, if needed later

- [x] **Phase 45: Prosody Preview Corpus** - Users can tune F5 timing against richer sanitized answer-shape previews. (completed 2026-07-09)
- [ ] **Phase 46: Timing Metrics Reports** - Users can compare presets with speech-rate and pause-distribution metrics.
- [ ] **Phase 47: Source-Type Pause Presets** - Users can choose, diagnose, and cache-track pause presets per answer source.

## Phase Details

### Phase 45: Prosody Preview Corpus
**Goal**: Users can tune F5 prosody against a richer sanitized corpus and selected subsets without committing private content.
**Depends on**: Phase 44 (v1.12 complete)
**Requirements**: CORP-01, CORP-02, CORP-03
**Success Criteria** (what must be TRUE):
  1. User can use sanitized preview phrases that cover short acknowledgements, standup updates, multi-sentence answers, clause-heavy responses, and direct handoff replies.
  2. User can generate current-vs-candidate A/B timing previews for selected corpus subsets.
  3. User can inspect or extend the preview corpus without committed artifacts containing private meeting transcript text, prompt text, response text, voice samples, training data, secrets, or raw audio.
**Plans**: 3 plans
Plans:
- [x] 45-01-PLAN.md - Built-in sanitized F5 preview corpus and inspection CLI.
- [x] 45-02-PLAN.md - Selected corpus subset preview support with safe metadata.
- [x] 45-03-PLAN.md - Artifact raw-text privacy regression and operator docs.

### Phase 46: Timing Metrics Reports
**Goal**: Users can compare F5 timing presets with objective speech-rate and pause-distribution evidence.
**Depends on**: Phase 45
**Requirements**: METR-01, METR-02, METR-03
**Success Criteria** (what must be TRUE):
  1. User can see total duration and normalized speech-rate metrics for each generated preview clip.
  2. User can see pause-distribution metrics grouped by sentence, clause, paragraph, and silent-breath continuation pauses.
  3. User can compare current and candidate presets in a sanitized report that highlights meaningful pace and pause changes.
  4. User can review timing metrics without exposing prompt text, response text, audio bytes, private meeting content, or secrets.
**Plans**: TBD

### Phase 47: Source-Type Pause Presets
**Goal**: Users can apply F5 pause presets by answer source while profile defaults, diagnostics, and cache staleness remain clear.
**Depends on**: Phase 46
**Requirements**: SRCE-01, SRCE-02, SRCE-03, SRCE-04
**Success Criteria** (what must be TRUE):
  1. User can configure separate F5 pause presets for source types such as prepared standup notes, response-cache variants, and spontaneous approved answers without hand-editing YAML for normal changes.
  2. User can rely on the existing profile-level preset when no source-type override is configured.
  3. User can trust source-type preset choices to participate in voice/cache fingerprints so affected prepared audio and response-cache artifacts become stale after timing changes.
  4. User can see active profile presets, source-type overrides, stale-artifact reasons, and targeted regeneration or review commands in cache-status, review, and readiness diagnostics.
**Plans**: TBD

## Requirement Coverage

| Requirement | Phase |
|-------------|-------|
| CORP-01 | Phase 45 |
| CORP-02 | Phase 45 |
| CORP-03 | Phase 45 |
| METR-01 | Phase 46 |
| METR-02 | Phase 46 |
| METR-03 | Phase 46 |
| SRCE-01 | Phase 47 |
| SRCE-02 | Phase 47 |
| SRCE-03 | Phase 47 |
| SRCE-04 | Phase 47 |

Coverage: 10/10 v1.13 requirements mapped. No orphaned requirements. No duplicate mappings.

## Progress

**Execution Order:**
Phases execute in numeric order: 45 -> 46 -> 47

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 45. Prosody Preview Corpus | 3/3 | Complete    | 2026-07-09 |
| 46. Timing Metrics Reports | 0/TBD | Not started | - |
| 47. Source-Type Pause Presets | 0/TBD | Not started | - |
