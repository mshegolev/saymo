# Phase 25 Context: Local Control Surface

**Milestone:** v1.6 Live Control Handbrake
**Status:** complete
**Date:** 2026-05-22

## Goal

Provide a local button-oriented surface for operating the handbrake without
requiring the user to memorize hotkeys during a call.

## Requirements

- UI-01: Open a local control surface with the primary handbrake controls.
- UI-02: Show current live-control state at a glance.
- UI-03: Use keyboard shortcuts that mirror configured macOS hotkey actions.
- UI-04: Expose additional live controls without crowding primary controls.
- SAFE-03: Record local audit events for handbrake actions.

## Implementation Notes

- Added `saymo live-control -p <profile>`.
- Added `saymo live-control-action -p <profile> --action <action>` for
  scriptable controls and future macOS automation.
- The TUI writes local commands consumed by a running `saymo auto` process.
- The panel displays state from `state.json` and lists all primary and optional
  controls.

