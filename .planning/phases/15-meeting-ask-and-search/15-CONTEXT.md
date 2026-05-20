# Phase 15: Meeting Ask And Search - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 15 builds read/retrieval features over Phase 14 meeting-memory ledgers:
search, cited meeting ask, and sanitized summary export. It should not draft
live answers from external task sources or add cockpit actions; those move to
Phases 16 and 17.

</domain>

<decisions>
## Implementation Decisions

### Search
- Search should scan local transcript ledgers under the existing profile
  `_sessions` hierarchy.
- Start with deterministic keyword/metadata filtering; defer SQLite/vector
  indexes until larger data makes that necessary.
- Filters should include profile, session, date range, speaker, category, and
  keyword.
- Empty or partial ledgers should produce clear diagnostics, not stack traces.

### Meeting Ask
- `meeting-ask` should answer with cited transcript evidence, not unsupported
  claims.
- The first implementation can be deterministic and citation-first; LLM-backed
  drafting is Phase 16.
- Citations should identify session id, segment sequence, and timestamp.
- If there is not enough evidence, the answer should say that directly.

### Sanitized Export
- Sanitized output should omit raw audio paths, secrets, config values, and
  full source sample paths.
- It can include aggregate counts and short transcript snippets when the local
  ledger retained transcript text.
- Export output should be markdown for easy review and sharing.
- Source evidence should stay local and profile/session-scoped.

### Claude's Discretion
None.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 14 added `saymo.analysis.meeting_memory` ledger/summary contracts.
- `saymo.commands.tests` already has `meeting-summary` and `_build_meeting_memory_ledger`.
- Session id resolution and sample-dir resolution are already shared in the CLI
  module.

### Established Patterns
- CLI commands use simple key/value and markdown output.
- Analysis helpers remain pure and unit-testable.
- Sanitized reports in diarization omit transcripts/audio unless explicitly
  needed; Phase 15 export should follow the same privacy posture.

### Integration Points
- Extend `saymo.analysis.meeting_memory` with search/ask/export helpers.
- Add `saymo meeting-search` and `saymo meeting-ask`.
- Extend `saymo meeting-summary` with sanitized export behavior.

</code_context>

<specifics>
## Specific Ideas

Use citation handles shaped like `session#sequence@start-end` so later answer
drafts can reuse the same evidence records.

</specifics>

<deferred>
## Deferred Ideas

- External Jira/Confluence/Obsidian/file source grounding moves to Phase 16.
- Live cockpit state and audit events move to Phase 17.
- Vector indexes and cross-session semantic search are future work.

</deferred>
