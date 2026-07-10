# Roadmap: Saymo v1.14 Call Dry-Run To Real Call

## Milestones

- 🚧 **v1.14 Call Dry-Run To Real Call** — Phases 48-51 (in progress)
- ✅ **v1.13 F5 Prosody Metrics** — Phases 45-47 shipped 2026-07-09.
  Archive: `.planning/milestones/v1.13-ROADMAP.md`

## Overview

v1.14 turns the existing call-ready, auto-preflight, rehearsal, LaunchAgent, and
F5 cache-readiness work into one operator dry-run before a real standup. The
milestone keeps dry-run checks explicit and non-destructive: it reports whether
Saymo is launch-ready, shows targeted repair commands, preserves protected
voice and cache assets, and writes sanitized evidence that can feed rehearsal,
scorecards, and safety-soak.

## Phases

**Phase Numbering:**
- Integer phases (48, 49, 50, 51): Planned v1.14 milestone work
- Decimal phases (49.1, 49.2): Urgent insertions, if needed later

- [x] **Phase 48: Dry-Run Orchestrator And Result Contract** - Users can run one non-destructive profile/provider dry-run and see a concise ready/not-ready result. (completed 2026-07-10)
- [x] **Phase 49: Source, Prepared Audio, Cache, And Voice Readiness** - Users can verify daily notes, prepared audio, response-cache coverage, and cloned-voice metadata with targeted repair guidance. (completed 2026-07-10)
- [x] **Phase 50: Provider, Audio, And Call-Control Health** - Users can verify provider, Chrome, BlackHole, audio routing, and LaunchAgent health without automatic provider repair. (completed 2026-07-10)
- [ ] **Phase 51: Dry-Run Evidence And Rehearsal Feedback** - Users can save sanitized dry-run evidence, feed it into reliability tools, and compare readiness changes.

## Phase Details

### Phase 48: Dry-Run Orchestrator And Result Contract
**Goal**: User can run one safe dry-run command that reports whether Saymo is ready for the next real standup without starting realtime mode or mutating protected assets.
**Depends on**: Phase 47 (v1.13 complete), existing call-ready and auto-preflight contracts
**Requirements**: DRY-01, DRY-02, DRY-03
**Success Criteria** (what must be TRUE):
  1. User can run one dry-run command for a selected profile and provider without starting `saymo auto` or realtime capture/playback.
  2. User can see one concise `ready` or `not ready` result with grouped blockers, warnings, exact actions, and rerun commands.
  3. User can trust dry-run mode to avoid synthesis, playback, cache deletion, retraining, voice model downloads, and protected `.saymo` asset mutation.
**Plans:** 2/2 plans complete
Plans:
- [x] 48-01-PLAN.md - RED tests for dry-run CLI, result, artifact, and non-destructive contracts.
- [x] 48-02-PLAN.md - GREEN implementation of dry-run command, renderer/artifact parameters, and command registration.

### Phase 49: Source, Prepared Audio, Cache, And Voice Readiness
**Goal**: User can prove source data, prepared standup audio, response-cache coverage, and approved cloned-voice metadata are launch-ready or receive targeted explicit repair commands.
**Depends on**: Phase 48
**Requirements**: SRC-01, SRC-02, SRC-03, CACHE-01, CACHE-02, VOICE-01
**Success Criteria** (what must be TRUE):
  1. User can have dry-run verify or create the selected Obsidian daily note without overwriting existing note content.
  2. User can see whether prepared standup audio matches the selected source hash, voice profile, and F5 source-type preset metadata.
  3. User can see response-cache coverage and staleness for the active profile using source-aware F5 `response_cache` metadata.
  4. User can verify approved cloned-voice profile readiness and stale voice metadata without touching training data or model checkpoints.
  5. User can read targeted repair guidance such as `saymo prepare -p <profile>` and `saymo prepare-responses -p <profile>` without automatic rebuilds or default `--force` use.
**Plans:** 2/2 plans complete
Plans:
- [x] 49-01-PLAN.md - RED tests for dry-run source flag, source/prepared/cache/voice metadata, targeted repair guidance, and safety guards.
- [x] 49-02-PLAN.md - GREEN implementation of dry-run source-only preparation, caller-aware readiness routing, and safe metadata/actions.

### Phase 50: Provider, Audio, And Call-Control Health
**Goal**: User can prove provider, Chrome tab, BlackHole routing, playback/capture devices, and call-control LaunchAgent health before joining a call, while repairs remain explicit.
**Depends on**: Phase 49
**Requirements**: ENV-01, ENV-02, ENV-03
**Success Criteria** (what must be TRUE):
  1. User can see provider tab readiness, Chrome/provider state, BlackHole capture/playback devices, and audio routing prerequisites in one dry-run result.
  2. User can see call-control daemon and LaunchAgent health, including heartbeat freshness, hotkey availability, and stale plist status.
  3. User can get exact restart, probe, and safe remediation commands for provider, audio, and control blockers.
  4. User can trust dry-run diagnostics not to kill apps, change meeting state, switch devices, or automatically repair provider state.
**Plans:** 2/2 plans complete
Plans:
- [x] 50-01-PLAN.md - RED tests for dry-run provider/audio/control diagnostics, exact remediation commands, call-ready compatibility, and no-auto-repair guards.
- [x] 50-02-PLAN.md - GREEN implementation for provider/audio dry-run rerun/action routing and call-control action clarity/safety.

### Phase 51: Dry-Run Evidence And Rehearsal Feedback
**Goal**: User can inspect sanitized dry-run evidence, reuse it in rehearsal/scorecard/safety-soak gates, and compare readiness changes before the real call.
**Depends on**: Phase 50
**Requirements**: EVID-01, EVID-02, EVID-03
**Success Criteria** (what must be TRUE):
  1. User can save a sanitized dry-run artifact with profile, provider, check statuses, stale reasons, actions, rerun commands, and timestamps.
  2. User can confirm dry-run artifacts exclude raw meeting text, prompt text, response text, audio bytes, secrets, voice samples, training data, and protected local assets.
  3. User can feed dry-run evidence into rehearsal, session scorecard, and safety-soak for a repeatable launch-readiness signal.
  4. User can compare the latest dry-run result with the previous result to see readiness improvements or regressions before joining a call.
**Plans**: TBD

## Requirement Coverage

| Requirement | Phase |
|-------------|-------|
| DRY-01 | Phase 48 |
| DRY-02 | Phase 48 |
| DRY-03 | Phase 48 |
| SRC-01 | Phase 49 |
| SRC-02 | Phase 49 |
| SRC-03 | Phase 49 |
| CACHE-01 | Phase 49 |
| CACHE-02 | Phase 49 |
| VOICE-01 | Phase 49 |
| ENV-01 | Phase 50 |
| ENV-02 | Phase 50 |
| ENV-03 | Phase 50 |
| EVID-01 | Phase 51 |
| EVID-02 | Phase 51 |
| EVID-03 | Phase 51 |

Coverage: 15/15 v1.14 requirements mapped. No orphaned requirements. No duplicate mappings.

## Progress

**Execution Order:**
Phases execute in numeric order: 48 -> 49 -> 50 -> 51

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 48. Dry-Run Orchestrator And Result Contract | 2/2 | Complete   | 2026-07-10 |
| 49. Source, Prepared Audio, Cache, And Voice Readiness | 2/2 | Complete   | 2026-07-10 |
| 50. Provider, Audio, And Call-Control Health | 2/2 | Complete   | 2026-07-10 |
| 51. Dry-Run Evidence And Rehearsal Feedback | 0/TBD | Not started | - |
