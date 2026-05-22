# Requirements: Saymo v1.6 Live Control Handbrake

**Defined:** 2026-05-22
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.6 Requirements

Requirements for milestone v1.6 Live Control Handbrake.

### Operator Guide

- [ ] **GUIDE-01**: User can read a short live-call guide that explains when to
  use speak, stop, auto-answer toggle, and manual takeover controls.
- [ ] **GUIDE-02**: User can see a clear answer to whether macOS hotkeys need
  the terminal focused, what process must be running, and which macOS
  permission is required.
- [ ] **GUIDE-03**: User can run a pre-call checklist that confirms profile,
  provider, audio devices, hotkeys, and manual takeover readiness.

### Handbrake State

- [ ] **CTRL-01**: User can switch auto-answer off during `saymo auto` so Saymo
  keeps the call safe and does not speak automatically while the user answers
  manually.
- [ ] **CTRL-02**: User can switch auto-answer back on without restarting the
  call assistant process.
- [ ] **CTRL-03**: User can stop current Saymo playback immediately without
  also losing the ability to continue listening or recover manually.
- [ ] **CTRL-04**: User can enter and exit manual takeover mode that pauses
  auto-answer, stops playback, and performs best-effort call microphone
  switching when the provider supports it.

### Control Surface

- [ ] **UI-01**: User can open a local control surface with obvious controls
  for auto-answer on/off, speak, stop, and manual takeover.
- [ ] **UI-02**: User can see the current live-control state at a glance:
  auto-answer on/off, paused, speaking, manual takeover, last trigger, and
  whether hotkeys are active.
- [ ] **UI-03**: User can operate the control surface with keyboard shortcuts
  that mirror the configured macOS hotkeys.

### macOS Hotkeys

- [ ] **HOT-01**: User can install or update the default Saymo hotkeys from a
  documented command without clobbering existing config values.
- [ ] **HOT-02**: User can verify before a call that global macOS hotkeys are
  registered, the Saymo listener is running, and Accessibility permission is
  available or missing.
- [ ] **HOT-03**: User can customize hotkeys per config/profile and see the
  effective binding names in preflight, guide, and runtime output.

### Safety And Audit

- [ ] **SAFE-02**: Saymo refuses all automatic speaking paths while auto-answer
  is off or manual takeover is active, including prepared responses and
  approved draft playback.
- [ ] **SAFE-03**: User can inspect a local audit trail for handbrake actions,
  including hotkey/button source, previous state, next state, blocked speaking
  reasons, and mic-switch result.
- [ ] **SAFE-04**: User can run focused regression checks proving stop, toggle,
  manual takeover, hotkey diagnostics, and disabled auto-answer behavior.

## Future Requirements

Deferred beyond v1.6.

### Native Menu Bar App

- User can control Saymo from a native macOS menu bar item without keeping a
  terminal window visible.

### Background Launch Agent

- User can run a persistent background Saymo control listener started by macOS
  login items or LaunchAgent.

### Provider-Specific Control Widgets

- User can see provider-specific mic/mute status directly in the control
  surface for every supported Chrome call provider.

### Voice Command Control

- User can say a local voice command such as "Saymo stop" or "Saymo pause" to
  trigger the same handbrake controls.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-speaking while auto-answer is off | The handbrake must be an absolute safety boundary. |
| Running hotkeys without a Saymo process | Global hotkeys need a live local listener; this milestone should make that explicit instead of hiding it. |
| Required native macOS app packaging | A local CLI/TUI control surface is enough to prove the control contract first. |
| Meeting-provider API bots | The goal is direct local control of the current Saymo process, not a bot that joins calls. |
| Cloud safety relay | Safety state must stay local and work without remote services. |
| Voice-command handbrake | Useful later, but risky to add before button/hotkey control is reliable. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GUIDE-01 | TBD | Pending |
| GUIDE-02 | TBD | Pending |
| GUIDE-03 | TBD | Pending |
| CTRL-01 | TBD | Pending |
| CTRL-02 | TBD | Pending |
| CTRL-03 | TBD | Pending |
| CTRL-04 | TBD | Pending |
| UI-01 | TBD | Pending |
| UI-02 | TBD | Pending |
| UI-03 | TBD | Pending |
| HOT-01 | TBD | Pending |
| HOT-02 | TBD | Pending |
| HOT-03 | TBD | Pending |
| SAFE-02 | TBD | Pending |
| SAFE-03 | TBD | Pending |
| SAFE-04 | TBD | Pending |

**Coverage:**
- v1.6 requirements: 16 total
- Mapped to phases: 0
- Unmapped: 16

---
*Requirements defined: 2026-05-22*
*Last updated: 2026-05-22 after initial v1.6 definition*
