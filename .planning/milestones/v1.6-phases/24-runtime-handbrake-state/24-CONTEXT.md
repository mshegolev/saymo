# Phase 24 Context: Runtime Handbrake State

**Milestone:** v1.6 Live Control Handbrake
**Status:** complete
**Date:** 2026-05-22

## Goal

Make auto-answer on/off and manual takeover explicit runtime safety state shared
by hotkeys, local controls, and playback gates.

## Requirements

- CTRL-01: Switch auto-answer off during `saymo auto`.
- CTRL-02: Switch auto-answer back on without restarting.
- CTRL-03: Stop current playback immediately and remain recoverable.
- CTRL-04: Enter and exit manual takeover with best-effort mic switching.
- SAFE-02: Block automatic speaking while handbrake state is active.

## Implementation Notes

- Added `LiveControlSnapshot`, command log, state file, and audit helpers in
  `saymo/analysis/live_control.py`.
- Wired `saymo auto` to publish state, poll local command actions, and share the
  same handler between hotkeys and local panel commands.
- Added explicit auto-answer, manual takeover, hard-disable, skip, status, and
  stop behavior.
- Preserved explicit manual speak while blocking automatic speaking when
  auto-answer is off, manual takeover is active, or hard-disable is active.

