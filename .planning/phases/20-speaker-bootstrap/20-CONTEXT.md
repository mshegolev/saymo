# Phase 20 Context: Speaker Bootstrap

## Goal

Turn completed sessions with `speaker=unknown` into usable speaker-labeled
training evidence through reviewed local workflows.

## Requirements

- SPKR-04: bootstrap speaker labels for a completed session without requiring
  always-on real-time diarization.
- SPKR-05: apply session-scoped speaker labels in bulk while preserving manual
  labels as authoritative and retaining audit metadata.
- QUAL-04: report speaker coverage and classifier-readiness impact after
  bootstrap.

## Existing System

- v1.3 writes optional diarization sidecars and reviewable speaker suggestions.
- `trigger-samples speaker-suggestion` applies one reviewed suggestion.
- `trigger-sessions summary` and Phase 18 progress already count speaker labels
  and readiness blockers.

## Design Decisions

- Add `trigger-sessions speaker-bootstrap` as a session-scoped command.
- Default to preview mode; require `--apply` before writing sample metadata.
- Preserve manual labels by only updating `speaker=unknown` unless
  `--overwrite-manual` is passed.
- Support both a lightweight manual label mode and a reviewed-suggestions mode.

