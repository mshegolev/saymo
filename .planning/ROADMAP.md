# Roadmap: Saymo v1.11 F5 Gap Hardening

## Overview

This brownfield milestone closes the remaining F5 silent-breath hardening gaps
from v1.10. It keeps the roadmap scoped to the active milestone: prove F5 cache
metadata goes stale when pacing changes, prove continuation pauses are silent,
guard the live-call path against audible breath injection, and make docs/config
clear that F5 "breath" behavior means silent timing only.

## Phases

- [x] **Phase 42: F5 Cache and Silence Gap Hardening** - Prove F5 prepared
  audio, response cache, diagnostics, continuation pauses, static guards, and
  docs/config all enforce the silent-breath boundary. (completed 2026-07-09)

## Phase Details

### Phase 42: F5 Cache and Silence Gap Hardening
**Goal**: User can trust that F5 live-call output remains silent-breath only,
with stale cache metadata detected, sanitized diagnostics, continuation silence
covered, and future audible-breath regressions guarded.
**Depends on**: Phase 41
**Requirements**: F5G-01, F5G-02, F5G-03, F5G-04, F5G-05, F5G-06
**Success Criteria** (what must be TRUE):
  1. User can verify prepared standup audio metadata created before an F5
     pacing change is treated as stale after any F5 pacing knob changes.
  2. User can verify response-cache metadata created before an F5 pacing change
     is treated as stale after any F5 pacing knob changes.
  3. User can inspect F5 cache-staleness diagnostics that expose stable
     sanitized reasons such as `voice_metadata_stale` without prompt text,
     response text, audio bytes, or private meeting content.
  4. User can verify `breath_interval_sentences` continuation pauses are
     zero-valued silence rather than non-zero breath or noise samples.
  5. User can rely on a regression/static guard proving the F5 live-call
     synthesis path does not import, call, or splice `load_breath_sample()`
     output, and can read docs/config examples that describe F5 breath behavior
     as silent timing only.
**Plans**: 1 plan

Plans:
- [x] 42-01-PLAN.md - Implement F5 cache stale checks, silence guards,
  sanitized diagnostics, and docs/config clarity.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| F5G-01 | Phase 42 | Complete |
| F5G-02 | Phase 42 | Complete |
| F5G-03 | Phase 42 | Complete |
| F5G-04 | Phase 42 | Complete |
| F5G-05 | Phase 42 | Complete |
| F5G-06 | Phase 42 | Complete |

**Coverage:**
- v1.11 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0

## Progress

**Execution Order:** Phase 42 only.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 42. F5 Cache and Silence Gap Hardening | 1/1 | Complete | 2026-07-09 |

## Next

Run `$gsd-audit-milestone`, then `$gsd-complete-milestone` if the audit passes.
