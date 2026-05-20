# Phase 12: Session Speaker Suggestions - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 12 runs or imports diarization for completed trigger-capture sessions and
stores reviewable speaker suggestions beside session ledgers. It must not
promote suggestions into sample `speaker` labels; promotion and quality gates
belong to Phase 13.

</domain>

<decisions>
## Implementation Decisions

### Session Scope
- Diarization runs by profile plus session id/prefix, reusing the v1.2 session
  ledger and sample metadata.
- Existing samples with no session id stay valid and are ignored by
  session-specific commands.
- Commands should accept deterministic segment JSON for tests/manual imports
  and use configured optional backends when no import file is provided.
- Missing backend availability should fail with a clear Click error, not a
  stack trace.

### Sidecar Storage
- Store diarization output under the existing profile `_sessions` directory as
  `<session_id>.diarization.json`.
- Sidecars include raw speaker segments, current speaker-id mappings, and
  per-sample suggestions.
- Suggestions include sample path, sequence, current manual label, inferred
  speaker id, suggested Saymo label, confidence, and overlap seconds.
- Manual sample metadata must not be overwritten in Phase 12.

### Speaker Mapping
- Add a session-level command to map backend speaker ids to `me`, `other`, or
  `unknown`.
- Updating a mapping should update sidecar suggestions only; sample JSON is not
  changed.
- Unmapped clusters should remain visible as unresolved suggestions.
- Output should be concise and grep-friendly for terminal review.

### Claude's Discretion
None.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TriggerSampleRecord` and `_iter_trigger_sample_records` already load sample
  paths, session ids, sequence numbers, speaker labels, and wav names.
- `trigger_sessions` already resolves session ids by exact/prefix match for
  summaries.
- Phase 11 added backend-neutral diarization result dataclasses and JSON
  helpers.

### Established Patterns
- CLI commands live in `saymo/commands/tests.py` and print plain diagnostic
  lines.
- Session metadata lives under `~/.saymo/trigger_samples/<profile>/_sessions/`.
- Metadata changes are local JSON writes with `ensure_ascii=False` and
  deterministic tests.

### Integration Points
- Extend `saymo.analysis.diarization` with sidecar helpers and suggestion
  matching.
- Add `trigger-sessions diarize`, `trigger-sessions speakers`, and
  `trigger-sessions map-speaker`.
- Add focused analysis and CLI tests.

</code_context>

<specifics>
## Specific Ideas

Use overlap between each sample's session sequence window and diarization
segments to choose the strongest speaker suggestion. Default window length can
match `trigger-capture --window` at 8 seconds and be overridable.

</specifics>

<deferred>
## Deferred Ideas

- Applying suggestions to sample `speaker` metadata is Phase 13.
- Speaker quality/conflict reports are Phase 13.
- Live-call diarization remains out of scope.

</deferred>
