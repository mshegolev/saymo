# Phase 22 Context: Regression Replay

## Goal

Make saved sessions reusable as a local reliability test for addressing,
question detection, speaker coverage, and live-assist readiness.

## Requirements

- REG-01: replay one saved capture session through current logic without
  re-recording audio.
- REG-02: report false handoffs, missed handoffs, question noise, speaker
  coverage, review coverage, and readiness.
- REG-03: compare before/after results and export sanitized reports.

## Existing System

- Trigger samples already store transcript metadata locally.
- `_evaluate_trigger_records` re-runs current deterministic trigger/addressing
  logic over saved samples.
- Phase 18 review progress and Phase 20 speaker bootstrap already expose the
  coverage primitives.

## Design Decisions

- Add a sanitized `regression_replay` analysis module.
- Add `trigger-sessions replay` for session-scoped CLI use.
- Export Markdown for humans and JSON for baseline comparison.
- Omit raw transcript and audio from replay reports.

