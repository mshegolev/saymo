# Roadmap: Saymo

## Overview

Milestone v1.9 focuses on Call Launch Readiness: making the pre-call path and
realtime loop operationally reliable through one call-ready gate, provider and
audio remediation, a terminal-independent local control daemon, fail-closed
realtime behavior, and sanitized evidence that feeds rehearsal, scorecard, and
safety-soak.

## Completed Milestones

- ✅ **v1.8 Call-ready Voice Clone** - Phases 31-35 shipped 2026-07-07.
  Archives: `.planning/milestones/v1.8-ROADMAP.md`,
  `.planning/milestones/v1.8-REQUIREMENTS.md`,
  `.planning/milestones/v1.8-MILESTONE-AUDIT.md`
- ✅ **v1.7 Live Reliability Rehearsal** - Phases 27-30 shipped 2026-07-07.
  Archives: `.planning/milestones/v1.7-ROADMAP.md`,
  `.planning/milestones/v1.7-REQUIREMENTS.md`,
  `.planning/milestones/v1.7-MILESTONE-AUDIT.md`,
  `.planning/milestones/v1.7-phases/`
- ✅ **v1.6 Live Control Handbrake** - Phases 23-26 shipped 2026-05-22.
  Archives: `.planning/milestones/v1.6-ROADMAP.md`,
  `.planning/milestones/v1.6-REQUIREMENTS.md`,
  `.planning/milestones/v1.6-MILESTONE-AUDIT.md`,
  `.planning/milestones/v1.6-phases/`
- ✅ **v1.5 Live Review + Safe Approved Speak** - Phases 18-22 shipped
  2026-05-21.
- ✅ **v1.4 Live Conversation Memory + Answer Cockpit** - Phases 14-17 shipped
  2026-05-20.
- ✅ **v1.3 Local Diarization Assist** - Phases 11-13 shipped 2026-05-20.
- ✅ **v1.2 Trigger Training Console** - Phases 8-10 shipped 2026-05-20.
- ✅ **v1.1 Call Intelligence Loop** - Phases 5-7 shipped 2026-05-18.
- ✅ **v1.0 Speedly Catcher + Speedly Sayer** - Phases 1-4 shipped
  2026-05-15.

## Active Milestone

- **v1.9 Call Launch Readiness** - Phases 36-40 planned.

## Phases

**Phase Numbering:**
- Integer phases (36, 37, 38, 39, 40): Planned milestone work
- Decimal phases (38.1, 38.2): Urgent insertions if needed

- [x] **Phase 36: Call-Ready Preflight and Cache Gate** - Create one (completed 2026-07-08)
  ready/not-ready launch gate for daily notes, prepared standup audio,
  response-cache coverage, cloned-voice metadata, and actionable remediation.
- [ ] **Phase 37: Provider and Audio Remediation** - Verify provider tab,
  Chrome capability, BlackHole routing, microphone takeover, permissions, and
  non-destructive remediation before realtime starts.
- [ ] **Phase 38: Local Call-Control Daemon and LaunchAgent** - Keep hotkeys,
  heartbeat, live-control status, and stop/takeover actions available outside
  the terminal through a local daemon and per-profile LaunchAgent.
- [ ] **Phase 39: Fail-Closed Realtime Meeting Loop** - Gate realtime startup
  and automatic answers so cache misses, stale voice metadata, provider loss,
  unsafe fallback, and handbrake state block playback.
- [ ] **Phase 40: Launch and Realtime Evidence Feedback** - Record sanitized
  launch and realtime evidence, then feed launch health and unsafe conditions
  back into scorecards, troubleshooting, and safety-soak.

## Phase Details

### Phase 36: Call-Ready Preflight and Cache Gate
**Goal**: User can run one call-ready flow that proves daily-note readiness,
prepared standup audio, response-cache coverage, approved cloned voice
metadata, and remediation before a call.
**Depends on**: v1.8 voice profile/cache gates, daily note helper, prepare
workflow, response cache, existing preflight/remediation patterns
**Requirements**: LAUN-01, LAUN-02, LAUN-03, LAUN-04, LAUN-05, LAUN-06, LAUN-07
**Success Criteria** (what must be TRUE):
  1. User can run one call-ready command for a profile and provider and see a
     concise `ready` or `not ready` result.
  2. User can have the launch flow create or verify today's Obsidian daily
     note while separately blocking placeholder or empty standup content.
  3. User can see whether prepared standup WAVs and response-cache variants
     are current for the selected profile, voice, response library, and cloned
     voice fingerprint.
  4. User can read grouped `block`, `warn`, and `info` remediation with exact
     actions and rerun commands for each failed launch check.
**Plans**: 4 plans

Plans:
- [x] 36-01: Add shared launch-readiness contracts and `call-ready` command shell
- [x] 36-02: Integrate daily-note source and prepared standup audio checks
- [x] 36-03: Add response-cache coverage and cloned-voice metadata blockers
- [x] 36-04: Add grouped remediation output, artifacts, and launch-gate tests

### Phase 37: Provider and Audio Remediation
**Goal**: User can verify provider, Chrome tab, BlackHole routing, microphone
takeover, and macOS permission readiness without destructive provider or system
audio actions.
**Depends on**: Phase 36 launch-readiness contract, provider abstractions,
Chrome automation helpers, audio routing/preflight checks, hotkey doctor
permission checks
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04, PROV-05
**Success Criteria** (what must be TRUE):
  1. User can see whether the configured provider and Chrome meeting tab are
     present, identifiable, actionable, and safe to use before realtime mode.
  2. User can verify BlackHole capture/playback routing and the real
     microphone takeover route before joining or starting the live loop.
  3. User can see provider capability limits, activation support, mic switching
     support, mute recovery, and unsupported-provider blockers without parsing
     raw errors.
  4. User can run provider/audio readiness checks with targeted permission
     remediation and no destructive Chrome, meeting, or system-route changes.
**Plans**: 4 plans

Plans:
- [ ] 37-01-PLAN.md - Add provider and Chrome tab readiness checks to launch readiness
- [ ] 37-02-PLAN.md - Add BlackHole route and microphone takeover verification
- [ ] 37-03-PLAN.md - Add provider capability and macOS permission remediation output
- [ ] 37-04-PLAN.md - Prove provider/audio checks are non-destructive with tests and artifacts

### Phase 38: Local Call-Control Daemon and LaunchAgent
**Goal**: User can keep the live-call handbrake reachable outside the terminal
and prove daemon, hotkey, heartbeat, command, and audit health before realtime
mode relies on it.
**Depends on**: Phase 36 launch-readiness contract, Phase 37 permission checks,
existing live-control command/state/audit files, global hotkey configuration,
macOS LaunchAgent conventions
**Requirements**: CTRL-01, CTRL-02, CTRL-03, CTRL-04, CTRL-05
**Success Criteria** (what must be TRUE):
  1. User can install, start, stop, restart, and inspect a per-profile Saymo
     call-control LaunchAgent from CLI commands.
  2. User can run a foreground call-control daemon that registers configured
     global hotkeys and publishes fresh heartbeat/status for the selected
     profile.
  3. User can see installed, loaded, running, stale, crash-looping, permission,
     and outdated-plist status in one daemon readiness result.
  4. User can queue existing live-control actions through daemon/status
     surfaces with the same command semantics and audit trail as CLI/hotkeys.
  5. User can prove handbrake reachability from heartbeat freshness, hotkey
     registration, command write/consume, and latest applied action evidence.
**Plans**: 5 plans

Plans:
- [ ] 38-01: Add foreground call-control daemon lifecycle and heartbeat model
- [ ] 38-02: Add LaunchAgent install, start, stop, restart, and status commands
- [ ] 38-03: Add daemon health diagnostics for stale heartbeat, crashes, permissions, and plist drift
- [ ] 38-04: Route daemon/status actions through existing live-control command and audit semantics
- [ ] 38-05: Add handbrake reachability probe, logs, docs, and tests

### Phase 39: Fail-Closed Realtime Meeting Loop
**Goal**: User can start realtime mode only through the shared launch gate, and
automatic speaking fails closed whenever cache, voice, provider, fallback, or
handbrake state is unsafe.
**Depends on**: Phases 36-38, existing `saymo auto` loop, response cache,
voice selector metadata, provider runtime checks, live-control state
**Requirements**: REAL-01, REAL-02, REAL-03, REAL-04, REAL-05, REAL-06
**Success Criteria** (what must be TRUE):
  1. User can start realtime mode only after launch-readiness passes for the
     selected profile, provider, cloned voice, cache, handbrake, trigger, and
     audio route.
  2. User can keep using the existing `saymo auto` workflow while any
     realtime alias shares the same launch-readiness gate.
  3. User can rely on automatic question handling to block cache misses, stale
     voice metadata, unsafe fallback, provider loss, manual takeover,
     hard-disable, and disabled auto-answer.
  4. User can manually trigger allowed prepared standup playback without that
     path becoming automatic cache-miss fallback.
  5. User can inspect sanitized realtime decision reasons for spoke, skipped,
     and blocked outcomes, while deterministic addressing and handbrake state
     remain the safety boundary.
**Plans**: 5 plans

Plans:
- [ ] 39-01: Wrap `saymo auto` and any realtime alias in the shared launch gate
- [ ] 39-02: Enforce fail-closed response-cache and cloned-voice metadata policy
- [ ] 39-03: Block playback on provider loss, takeover, hard-disable, and disabled auto-answer
- [ ] 39-04: Preserve explicit manual standup playback without automatic cache-miss fallback
- [ ] 39-05: Emit sanitized realtime decision events and add regression tests

### Phase 40: Launch and Realtime Evidence Feedback
**Goal**: User can inspect sanitized launch and realtime evidence, see health
signals in scorecards, and run safety-soak gates that fail on v1.9 launch or
runtime safety regressions.
**Depends on**: Phases 36-39, existing launch/rehearsal artifacts,
session-scorecard, safety-soak, remediation hints
**Requirements**: EVID-01, EVID-02, EVID-03, EVID-04, EVID-05
**Success Criteria** (what must be TRUE):
  1. User can inspect sanitized launch-readiness artifacts containing checks,
     blocker categories, cache counts, voice/cache fingerprints, provider
     status, daemon status, mode, and rerun commands.
  2. User can inspect sanitized realtime events for launch start/end, cache
     hits/misses, fallback blocks, provider failures, playback attempts,
     handbrake actions, and stop reasons.
  3. User can see launch health, daemon/control availability, cache hit/miss
     counts, unsafe fallback blocks, and provider drift in rehearsal or
     session scorecards.
  4. User can run safety-soak against v1.9 evidence and get a failed gate for
     unsafe playback, stale cache, missing daemon readiness, provider blockers,
     or unapproved fallback conditions.
  5. User can troubleshoot failures from sanitized evidence that includes
     log/artifact paths and next rerun commands.
**Plans**: 4 plans

Plans:
- [ ] 40-01: Define and write sanitized launch-readiness artifact schema
- [ ] 40-02: Feed realtime and launch-health evidence into rehearsal/session scorecards
- [ ] 40-03: Extend safety-soak with v1.9 readiness, daemon, cache, and fallback gates
- [ ] 40-04: Add troubleshooting output, rerun commands, docs, and evidence tests

## Progress

**Execution Order:**
Phases execute in numeric order: 36 -> 37 -> 38 -> 39 -> 40

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 36. Call-Ready Preflight and Cache Gate | v1.9 | Complete    | 2026-07-08 | 2026-07-08 |
| 37. Provider and Audio Remediation | v1.9 | 0/4 | Not started | - |
| 38. Local Call-Control Daemon and LaunchAgent | v1.9 | 0/5 | Not started | - |
| 39. Fail-Closed Realtime Meeting Loop | v1.9 | 0/5 | Not started | - |
| 40. Launch and Realtime Evidence Feedback | v1.9 | 0/4 | Not started | - |

## Requirement Coverage

| Requirement | Phase |
|-------------|-------|
| LAUN-01 | Phase 36 |
| LAUN-02 | Phase 36 |
| LAUN-03 | Phase 36 |
| LAUN-04 | Phase 36 |
| LAUN-05 | Phase 36 |
| LAUN-06 | Phase 36 |
| LAUN-07 | Phase 36 |
| PROV-01 | Phase 37 |
| PROV-02 | Phase 37 |
| PROV-03 | Phase 37 |
| PROV-04 | Phase 37 |
| PROV-05 | Phase 37 |
| CTRL-01 | Phase 38 |
| CTRL-02 | Phase 38 |
| CTRL-03 | Phase 38 |
| CTRL-04 | Phase 38 |
| CTRL-05 | Phase 38 |
| REAL-01 | Phase 39 |
| REAL-02 | Phase 39 |
| REAL-03 | Phase 39 |
| REAL-04 | Phase 39 |
| REAL-05 | Phase 39 |
| REAL-06 | Phase 39 |
| EVID-01 | Phase 40 |
| EVID-02 | Phase 40 |
| EVID-03 | Phase 40 |
| EVID-04 | Phase 40 |
| EVID-05 | Phase 40 |

**Coverage:** 28/28 v1.9 requirements mapped. No orphaned requirements. No
duplicate requirement assignments.
