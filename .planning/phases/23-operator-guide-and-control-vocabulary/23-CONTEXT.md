# Phase 23 Context: Operator Guide And Control Vocabulary

**Milestone:** v1.6 Live Control Handbrake
**Status:** complete
**Date:** 2026-05-22

## Goal

Give the operator a short, accurate live-call guide and stable names for every
emergency control before runtime behavior and CLI output diverge.

## Requirements

- GUIDE-01: Explain speak, stop, auto-answer toggle, and manual takeover.
- GUIDE-02: Explain terminal focus, running Saymo process, and macOS
  Accessibility permission.

## Implementation Notes

- Added `docs/LIVE-CONTROL-HANDBRAKE.md` as the primary operator guide.
- Updated `README.md` with the pre-call command sequence and hotkey table.
- Added a shared action catalog in `saymo/analysis/live_control.py` so guide,
  runtime output, hotkey doctor, and control surfaces use the same labels.
- Added docs tests in `tests/test_live_control_docs.py`.

