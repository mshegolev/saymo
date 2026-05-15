# Phase 4 Context: Sample Review Workflow

## Goal

Turn captured call windows into a practical local review loop for trigger
training and debugging.

## Existing Baseline

- `trigger-capture` produced sample folders, WAV files, and adjacent JSON.
- Users still had to inspect raw JSON or manually pick files to understand
  what was captured.
- There was no sanitized report export.

## Decisions

- Add one command group, `saymo trigger-samples`, for list/replay/report.
- `list` may print transcripts because it is an explicit local inspection
  command.
- `report` omits transcript text and raw audio references beyond sample
  basenames.

