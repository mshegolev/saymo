# v1.4 Research Summary: Live Conversation Memory + Answer Cockpit

## Stack Additions

- Extend local trigger-session storage into a full-session transcript ledger.
- Add deterministic local meeting-memory retrieval before heavier vector or
  database dependencies.
- Add answer-draft and cockpit contracts that separate trigger evidence,
  citations, generated text, user action, and playback.
- Add a local audit ledger for trigger/draft/action/spoken-response events.

## Feature Table Stakes

- Full-session transcript ledger with speaker, time, confidence, category, and
  source-window metadata.
- Per-session summaries and local search across current/past meetings.
- `meeting-ask` style command that answers with citations to transcript
  evidence.
- Source-grounded answer drafts using meeting memory plus configured Jira,
  Confluence, Obsidian, and file sources.
- Live answer cockpit with speak/edit/skip/takeover approval.
- Audit trail for why Saymo triggered, what it drafted, what sources it used,
  and what the user chose.

## Watch Outs

- Full transcripts are sensitive; keep storage local, configurable, and
  sanitizable.
- Do not let generated drafts bypass explicit user approval before live speech.
- Keep bot-join, cloud streaming, GUI-first, and native macOS capture work out
  of the critical path for this milestone.
- Preserve deterministic trigger gating and manual takeover while adding
  retrieval and answer drafting.

## Roadmap Implication

Phase 14 should establish full-session memory ledgers. Phase 15 should add
search and question answering over local sessions. Phase 16 should add
source-grounded answer drafts. Phase 17 should provide the live cockpit action
gate and audit trail.
