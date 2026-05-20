# Phase 16: Grounded Answer Drafts - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 16 generates reviewable answer drafts from local meeting-memory evidence
and configured source-plugin context. It should not add live cockpit actions or
audit replay; those are Phase 17.

</domain>

<decisions>
## Implementation Decisions

### Draft Contracts
- Store trigger evidence, citations, source diagnostics, draft text,
  confidence, and approval state separately.
- Drafts should be JSON-serializable so Phase 17 can audit or replay them.
- A draft is never equivalent to approval to speak.
- Missing evidence should lower confidence and be visible in output.

### Context Assembly
- Reuse Phase 15 meeting-memory citations as the primary evidence source.
- Fetch configured source plugins through the existing plugin discovery system.
- Default source selection should follow the meeting profile/source config and
  allow explicit CLI overrides.
- Source snippets should be summarized/sanitized before inclusion in CLI output.

### Composer Path
- Provide a deterministic draft by default so tests and dry runs do not need
  Ollama.
- Add an optional local composer mode that calls existing Ollama QA composer
  when the user requests it.
- If source plugins fail or return no content, preserve diagnostics instead of
  failing the whole draft.
- Keep private names out of source code; all user/project context comes from
  config or local data.

### Claude's Discretion
None.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.analysis.meeting_memory` provides `answer_meeting_question` and cited
  search results.
- `saymo.plugins.base.get_plugin` can fetch configured source context.
- `saymo.speech.ollama_composer.answer_question` can optionally compose a local
  answer.

### Established Patterns
- Configurable prompts live in `saymo/speech/ollama_composer.py`.
- Source plugins return dicts with `yesterday`, `today`, and date fields.
- CLI diagnostic commands should keep running when optional sources are absent.

### Integration Points
- Add `saymo.analysis.answer_cockpit` for draft/source/trigger evidence
  contracts; Phase 17 will extend the same module with cockpit/audit helpers.
- Add `saymo answer-draft`.
- Add tests for deterministic drafts and source diagnostics.

</code_context>

<specifics>
## Specific Ideas

Draft output should show the current question/handoff text, meeting citations,
source freshness, missing-source diagnostics, confidence, and the draft body.

</specifics>

<deferred>
## Deferred Ideas

- Speak/edit/skip/takeover action handling moves to Phase 17.
- Persistent audit trail moves to Phase 17.

</deferred>
