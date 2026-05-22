# Roadmap: Saymo

## Overview

Milestone v1.6 focuses on Live Control Handbrake: giving the user a visible,
fast, local way to disable auto-answering, stop playback, take the microphone
back, and re-enable Saymo safely during a live call.

## Completed Milestones

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

- **v1.6 Live Control Handbrake** - Phases 23-26 planned.

## Phases

**Phase Numbering:**
- Integer phases (23, 24, 25, 26): Planned milestone work
- Decimal phases (24.1, 24.2): Urgent insertions if needed

- [ ] **Phase 23: Operator Guide And Control Vocabulary** - Define the live
  call guide, control names, and expected operator flow before code changes.
- [ ] **Phase 24: Runtime Handbrake State** - Add one safety state model for
  auto-answer on/off, stop, pause, and manual takeover.
- [ ] **Phase 25: Local Control Surface** - Add buttons/keyboard controls that
  expose the handbrake state without relying on hidden terminal output.
- [ ] **Phase 26: macOS Hotkey Doctor And Safety Regression** - Make hotkeys
  installable, diagnosable, customizable, and regression-tested.

## Phase Details

### Phase 23: Operator Guide And Control Vocabulary
**Goal**: Give the user a short, accurate live-call guide and stable names for
every emergency control before implementation details spread across CLI output.
**Depends on**: Existing README hotkey section, `scripts/add_hotkeys.py`,
current `saymo auto` hotkey behavior
**Requirements**: GUIDE-01, GUIDE-02
**Success Criteria** (what must be TRUE):
  1. The guide explains when to press speak, stop, auto-answer toggle, and
     manual takeover during a live meeting.
  2. The guide answers whether the terminal must be focused: no, but a Saymo
     process must be running and macOS Accessibility permission must allow
     global hotkeys.
  3. User-facing labels for states and controls are consistent across docs,
     preflight, runtime logs, and the future control surface.
  4. The guide does not promise native menu bar, background daemon, or voice
     command control in v1.6.
**Plans**: 3 plans

Plans:
- [ ] 23-01: Write short live-call handbrake guide
- [ ] 23-02: Define control/state vocabulary and map existing hotkeys
- [ ] 23-03: Add docs tests or link checks for current behavior claims

### Phase 24: Runtime Handbrake State
**Goal**: Make auto-answer on/off and manual takeover an explicit runtime
safety boundary shared by hotkeys, future buttons, and playback gates.
**Depends on**: Phase 23, existing `saymo auto` pause/takeover helpers,
approved draft playback gates
**Requirements**: CTRL-01, CTRL-02, CTRL-03, CTRL-04, SAFE-02
**Success Criteria** (what must be TRUE):
  1. Auto-answer can be switched off during `saymo auto` without stopping the
     process or losing manual recovery.
  2. Auto-answer can be switched back on after the user answers manually.
  3. Stop cancels current playback immediately and leaves the assistant in a
     known recoverable state.
  4. Manual takeover pauses auto-answer, stops playback, and performs
     best-effort provider mic switching without making unsupported providers
     fail the call flow.
  5. Prepared responses and approved draft playback are both blocked while
     auto-answer is off or manual takeover is active.
**Plans**: 4 plans

Plans:
- [ ] 24-01: Add shared live-control state model and transition helpers
- [ ] 24-02: Wire auto-answer toggle into `saymo auto` response gates
- [ ] 24-03: Normalize stop and manual takeover recovery behavior
- [ ] 24-04: Add tests for blocked automatic speaking while handbrake is active

### Phase 25: Local Control Surface
**Goal**: Provide a local button-oriented surface for operating the handbrake
without relying on memory of hotkey combinations during a live call.
**Depends on**: Phase 24, existing `saymo dashboard` TUI
**Requirements**: UI-01, UI-02, UI-03, SAFE-03
**Success Criteria** (what must be TRUE):
  1. A user can open a local control surface showing Auto Answer, Speak, Stop,
     and Takeover controls.
  2. The surface shows current state: auto-answer on/off, paused, speaking,
     manual takeover, last trigger, and hotkey listener state.
  3. Keyboard controls inside the surface mirror configured macOS hotkeys.
  4. Handbrake actions record audit events with source, previous state, next
     state, blocked reason, and mic-switch result.
  5. Existing `saymo dashboard` prepare/speak behavior remains usable.
**Plans**: 4 plans

Plans:
- [ ] 25-01: Extend or add local dashboard handbrake controls
- [ ] 25-02: Render live-control state and last-action feedback
- [ ] 25-03: Add keyboard shortcuts matching configured hotkey actions
- [ ] 25-04: Record handbrake audit events from button and keyboard actions

### Phase 26: macOS Hotkey Doctor And Safety Regression
**Goal**: Make global hotkeys predictable before a call and regression-test the
full handbrake flow.
**Depends on**: Phases 23-25, existing hotkey install helper and
`takeover-check`
**Requirements**: GUIDE-03, HOT-01, HOT-02, HOT-03, SAFE-04
**Success Criteria** (what must be TRUE):
  1. User can install or update default hotkeys without clobbering existing
     config values.
  2. User can run a pre-call checklist that reports profile, provider, audio
     devices, hotkeys, process/listener assumptions, and manual takeover
     readiness.
  3. Hotkey diagnostics explain missing macOS Accessibility permission, missing
     Saymo listener process, and effective configured bindings.
  4. Per-profile or config-customized bindings are reflected in docs, preflight,
     runtime output, and control surface labels.
  5. Focused tests cover stop, toggle, takeover, hotkey diagnostics, and
     disabled auto-answer behavior.
**Plans**: 4 plans

Plans:
- [ ] 26-01: Improve hotkey install/update command and guide snippets
- [ ] 26-02: Add hotkey doctor/pre-call checklist diagnostics
- [ ] 26-03: Surface effective customized bindings consistently
- [ ] 26-04: Add focused handbrake and hotkey regression tests

## Progress

**Execution Order:**
Phases execute in numeric order: 23 -> 24 -> 25 -> 26

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 23. Operator Guide And Control Vocabulary | v1.6 | 0/3 | Pending | - |
| 24. Runtime Handbrake State | v1.6 | 0/4 | Pending | - |
| 25. Local Control Surface | v1.6 | 0/4 | Pending | - |
| 26. macOS Hotkey Doctor And Safety Regression | v1.6 | 0/4 | Pending | - |

## Requirement Coverage

| Requirement | Phase |
|-------------|-------|
| GUIDE-01 | Phase 23 |
| GUIDE-02 | Phase 23 |
| GUIDE-03 | Phase 26 |
| CTRL-01 | Phase 24 |
| CTRL-02 | Phase 24 |
| CTRL-03 | Phase 24 |
| CTRL-04 | Phase 24 |
| UI-01 | Phase 25 |
| UI-02 | Phase 25 |
| UI-03 | Phase 25 |
| HOT-01 | Phase 26 |
| HOT-02 | Phase 26 |
| HOT-03 | Phase 26 |
| SAFE-02 | Phase 24 |
| SAFE-03 | Phase 25 |
| SAFE-04 | Phase 26 |

**Coverage:** 16/16 requirements mapped.
