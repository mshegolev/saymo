# Roadmap: Saymo v1.12 F5 Voice Tuning Controls

## Overview

This brownfield milestone turns the F5 timing work from hardcoded tuning into
an operator-controlled loop: list/select named pause presets, generate safe A/B
timing previews, record preference reviews, apply chosen timing without manual
YAML edits, and keep cache/review metadata safety intact.

The milestone does not retrain the voice model, switch providers, inject
audible breath/noise, or automatically delete/rebuild real caches.

## Phases

- [x] **Phase 43: F5 Pause Presets and A/B Timing Review** - Add named F5
  pause presets, profile selection, A/B preview artifacts, preference review,
  and safe apply behavior. (completed 2026-07-09)
- [ ] **Phase 44: Cache Regeneration and Review Metadata Safety** - Add
  operator warnings for expensive stale-cache regeneration, targeted
  remediation, `saymo review` sidecar preservation, and metadata-safe legacy
  lookup behavior.

## Phase Details

### Phase 43: F5 Pause Presets and A/B Timing Review
**Goal**: User can compare and apply F5 timing presets by ear without manual
config edits, retraining, or breaking the existing cache fingerprint contract.
**Depends on**: Phase 42
**Requirements**: PAUSE-01, PAUSE-02, PAUSE-03, TUNE-01, TUNE-02, TUNE-03
**Success Criteria** (what must be TRUE):
  1. User can list named F5 pause presets and inspect sentence, clause,
     paragraph, and silent-breath timing values.
  2. User can select a named preset for a meeting profile without hand-editing
     YAML.
  3. User can generate A/B WAV previews comparing current timing to a
     candidate preset using the approved local F5 voice profile.
  4. User can record a simple preference review and see a recommended preset
     or knob set.
  5. User can apply the selected timing so prepared-audio and response-cache
     metadata use the updated F5 pacing fingerprint.
  6. Preview/review artifacts are sanitized and do not copy private meeting
     transcript, prompt text, secrets, or training data into committed files.
**Plans**: 2 plans

Plans:
- [x] 43-01-PLAN.md - Implement preset catalog, profile selection, config
  persistence, and fingerprint integration.
- [x] 43-02-PLAN.md - Implement A/B preview generation, review recording,
  recommendation output, and sanitized artifact checks.

### Phase 44: Cache Regeneration and Review Metadata Safety
**Goal**: User can understand and repair stale F5 cache state without wasteful
regeneration, while `saymo review` and legacy cache helpers preserve voice
metadata safety.
**Depends on**: Phase 43
**Requirements**: CACHE-01, CACHE-02, CACHE-03, CACHE-04
**Success Criteria** (what must be TRUE):
  1. User sees an explicit warning when prepared audio or response cache is
     stale and regeneration may be expensive.
  2. User gets targeted prepare/cache commands that avoid unnecessary
     regeneration when current artifacts are still valid.
  3. User can run `saymo review` without losing the prepared-audio metadata
     sidecar required by call-ready checks.
  4. Response-cache lookup helpers enforce metadata checks consistently across
     active and legacy code paths.
  5. Cache warning and review diagnostics stay sanitized and avoid prompt text,
     response text, raw audio bytes, private meeting content, and secrets.
**Plans**: 2 plans

Plans:
- [ ] 44-01-PLAN.md - Implement stale-cache cost warnings and targeted
  remediation commands.
- [ ] 44-02-PLAN.md - Preserve `saymo review` metadata sidecars and harden
  legacy response-cache lookup metadata checks.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PAUSE-01 | Phase 43 | Complete |
| PAUSE-02 | Phase 43 | Complete |
| PAUSE-03 | Phase 43 | Complete |
| TUNE-01 | Phase 43 | Complete |
| TUNE-02 | Phase 43 | Complete |
| TUNE-03 | Phase 43 | Complete |
| CACHE-01 | Phase 44 | Pending |
| CACHE-02 | Phase 44 | Pending |
| CACHE-03 | Phase 44 | Pending |
| CACHE-04 | Phase 44 | Pending |

**Coverage:**
- v1.12 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

## Progress

**Execution Order:** Phase 43, then Phase 44.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 43. F5 Pause Presets and A/B Timing Review | 2/2 | Complete | 2026-07-09 |
| 44. Cache Regeneration and Review Metadata Safety | 0/2 | Not started | - |

## Next

Run `$gsd-discuss-phase 44` to gather implementation context, or
`$gsd-plan-phase 44` to plan directly.
