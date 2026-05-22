# Phase 26 Context: macOS Hotkey Doctor And Safety Regression

**Milestone:** v1.6 Live Control Handbrake
**Status:** complete
**Date:** 2026-05-22

## Goal

Make global hotkeys predictable before a call and regression-test the full
handbrake flow.

## Requirements

- GUIDE-03: Pre-call checklist command.
- HOT-01: Install/update defaults without clobbering existing config.
- HOT-02: Verify listener/process and Accessibility assumptions.
- HOT-03: Show effective customized bindings consistently.
- HOT-04: Configure optional global hotkeys.
- SAFE-04: Focused regression checks for the handbrake flow.

## Implementation Notes

- Added `saymo hotkey-doctor`.
- Expanded `scripts/add_hotkeys.py`, `config.example.yaml`, and `SafetyConfig`
  with optional action hotkeys.
- `saymo auto` now registers configured bindings from the shared action
  catalog.
- Added focused tests for hotkey install script, doctor output, config parsing,
  CLI command queue, docs, and automatic-speaking gates.

