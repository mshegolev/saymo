# v1.4 Research: Architecture

## Existing Integration Points

- `saymo.analysis.trigger_capture` records classified call windows and sample
  metadata.
- `saymo.analysis.trigger_sessions` owns capture-session ledgers, summaries,
  and profile/session lookup.
- `saymo.analysis.diarization` stores optional speaker sidecars and suggestions
  beside sessions.
- `saymo.analysis.turn_detector` and classifier readiness decide whether a live
  window looks addressed to the user.
- `saymo.speech.ollama_composer` composes local responses from source context.
- `saymo.plugins` fetch configured task/notes/file context.
- `saymo.commands.tests` currently hosts most diagnostic/review CLI commands.

## Proposed Components

- `saymo.analysis.meeting_memory`
  - transcript segment contracts
  - session transcript ledger load/save helpers
  - search filters and cited retrieval results
  - per-session summary rendering
- `saymo.analysis.answer_cockpit`
  - trigger evidence contracts
  - answer draft contracts with citations and confidence
  - action state: speak, edit, skip, takeover
  - audit event writer
- CLI additions
  - `saymo meeting-summary`
  - `saymo meeting-search`
  - `saymo meeting-ask`
  - `saymo answer-draft`
  - `saymo answer-cockpit`
  - `saymo answer-audit`

## Data Flow

1. A live or dry-run capture session records transcript segments and classified
   trigger windows under the existing local session hierarchy.
2. Meeting memory normalizes those segments into a chronological ledger with
   speaker, category, confidence, source window, and storage metadata.
3. Search and `meeting-ask` retrieve cited transcript evidence from current or
   selected past sessions.
4. When Saymo detects a handoff, answer drafting combines trigger evidence,
   meeting-memory snippets, and configured source-plugin context.
5. The cockpit shows the draft and citations, then records the user's explicit
   speak/edit/skip/takeover decision.
6. Spoken responses and skipped/taken-over events are appended to the local
   audit ledger for debugging and training.

## Build Order

1. Full-session transcript ledger and summaries.
2. Local search and ask commands over session memory.
3. Source-grounded answer draft contracts and composer wiring.
4. Live cockpit actions and audit trail.
