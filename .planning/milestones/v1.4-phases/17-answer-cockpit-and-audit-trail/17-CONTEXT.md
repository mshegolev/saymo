# Phase 17: Answer Cockpit And Audit Trail - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 17 adds the explicit review/control layer on top of Phase 16 answer
drafts: cockpit state, speak/edit/skip/takeover actions, and local audit trail.
It should not auto-speak unapproved generated drafts by default.

</domain>

<decisions>
## Implementation Decisions

### Cockpit State
- Start with CLI/TUI-compatible output and JSON state; defer a GUI.
- Cockpit state should point to the current draft and expose action choices.
- A draft starts pending and requires explicit action before speech is
  considered approved.
- The state file should live next to the local session sidecars.

### Actions
- Supported actions are speak, edit, skip, and takeover.
- `speak` records approval; actual audio playback remains opt-in/future
  integration with existing speak paths.
- `edit` stores the edited text as the approved draft text.
- `skip` and `takeover` are first-class outcomes, not errors.

### Audit Trail
- Audit events should be local JSONL under the profile/session `_sessions`
  directory.
- Events should include trigger/draft/action/speech metadata without raw audio
  payloads or secrets.
- Add list/report/replay-friendly CLI output.
- Keep audit rendering sanitized.

### Claude's Discretion
None.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 16 `AnswerDraft` JSON files can be reused as cockpit draft inputs.
- `saymo.analysis.meeting_memory.meeting_transcript_path` establishes sidecar
  path conventions.
- Existing hotkeys already queue/manual takeover in live auto-mode; Phase 17
  should expose compatible action names rather than changing live hotkeys.

### Established Patterns
- Sidecars live under `<samples>/<profile>/_sessions/`.
- CLI commands print grep-friendly status and paths.
- Sanitized reports avoid raw audio and private config values.

### Integration Points
- Extend `saymo.analysis.answer_cockpit` with cockpit state and audit helpers.
- Add `saymo answer-cockpit show/action`.
- Add `saymo answer-audit list/report`.

</code_context>

<specifics>
## Specific Ideas

The cockpit should show the same information as a future UI would need:
trigger evidence, draft text, citations, confidence, source status, and action
choices.

</specifics>

<deferred>
## Deferred Ideas

- Actual live audio playback from a generated draft can be wired later through
  existing TTS/playback safety gates.
- A desktop/browser cockpit UI is future work after CLI contracts stabilize.

</deferred>
