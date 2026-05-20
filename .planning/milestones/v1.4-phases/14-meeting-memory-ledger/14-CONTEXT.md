# Phase 14: Meeting Memory Ledger - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 14 turns existing trigger-capture sessions into local full-session
transcript ledgers and readable summaries. It should not implement meeting
question answering, answer drafting, or cockpit actions; those belong to
Phases 15-17.

</domain>

<decisions>
## Implementation Decisions

### Storage Shape
- Extend the existing `~/.saymo/trigger_samples/<profile>/_sessions/` layout
  with a transcript sidecar rather than adding a new database.
- Store JSON-compatible, Saymo-owned dataclasses for segments and summaries.
- Keep source sample paths local and never write raw audio bytes into transcript
  ledgers.
- Existing trigger sessions without transcript sidecars must remain listable.

### Segment Metadata
- Build segments from saved trigger sample metadata: sequence, timestamp,
  transcript, category, speaker, trigger/question flags, confidence, and source
  window.
- Derive start/end seconds from session sequence and configured window length.
- Treat missing transcript text as incomplete coverage, not as a hard failure.
- Preserve manual speaker labels as authoritative while allowing diarization
  suggestions to remain sidecars.

### CLI Output
- Add a dedicated meeting-memory build command and a concise
  `meeting-summary` command.
- Output should be grep-friendly and include ledger paths.
- Summary output can show local transcript excerpts because it is an explicit
  local command; sanitized export is Phase 15.
- Do not require any cloud service or live call to build a ledger from saved
  samples.

### Claude's Discretion
None.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.analysis.trigger_sessions` already resolves session ledgers and sample
  summaries.
- `saymo.commands.tests` already contains trigger-session CLI groups and sample
  record loaders.
- `tests/analysis/test_trigger_sessions.py` provides helpers for writing sample
  metadata.

### Established Patterns
- Session sidecars live under `<samples>/<profile>/_sessions/`.
- Click commands print simple key/value diagnostics.
- Tests cover pure analysis helpers first, then CLI output through
  `CliRunner`.

### Integration Points
- Add `saymo.analysis.meeting_memory`.
- Add config defaults in `saymo.config` and `config.example.yaml`.
- Add CLI commands in `saymo.commands.tests`.
- Add tests under `tests/analysis/` and CLI coverage in `tests/test_trigger_check.py`.

</code_context>

<specifics>
## Specific Ideas

Keep the first ledger implementation JSON-based and deterministic. SQLite,
vector indexes, and GUI surfaces are deferred until local session memory proves
useful.

</specifics>

<deferred>
## Deferred Ideas

- Local meeting search and ask commands move to Phase 15.
- Source-grounded answer drafts move to Phase 16.
- Cockpit actions and audit replay move to Phase 17.

</deferred>
