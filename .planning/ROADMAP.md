# Roadmap: Saymo

## Overview

Milestone v1.4 focuses on Live Conversation Memory + Answer Cockpit: extending
Saymo from isolated trigger-sample capture into local full-session memory,
searchable meeting recall, source-grounded answer drafts, and an explicit
cockpit action gate before live speech.

## Completed Milestones

- ✅ **v1.3 Local Diarization Assist** - Phases 11-13 shipped 2026-05-20.
  Archives: `.planning/milestones/v1.3-ROADMAP.md`,
  `.planning/milestones/v1.3-REQUIREMENTS.md`,
  `.planning/milestones/v1.3-MILESTONE-AUDIT.md`
- ✅ **v1.2 Trigger Training Console** - Phases 8-10 shipped 2026-05-20.
  Archive: `.planning/milestones/v1.2-ROADMAP.md`
- ✅ **v1.1 Call Intelligence Loop** - Phases 5-7 shipped 2026-05-18.
  Archive: `.planning/milestones/v1.1-ROADMAP.md`
- ✅ **v1.0 Speedly Catcher + Speedly Sayer** - Phases 1-4 shipped
  2026-05-15.

## Active Milestone

- **v1.4 Live Conversation Memory + Answer Cockpit** - Phases 14-17 planned.

## Phases

**Phase Numbering:**
- Integer phases (14, 15, 16, 17): Planned milestone work
- Decimal phases (15.1, 15.2): Urgent insertions if needed

- [x] **Phase 14: Meeting Memory Ledger** - Save full-session transcript
  ledgers and summaries for recorded call sessions.
- [x] **Phase 15: Meeting Ask And Search** - Search local sessions and answer
  questions with transcript citations.
- [x] **Phase 16: Grounded Answer Drafts** - Generate source-backed drafts from
  meeting memory and configured context sources.
- [x] **Phase 17: Answer Cockpit And Audit Trail** - Show live handoff
  evidence, approve/edit/skip/takeover actions, and audit what happened.

## Phase Details

### Phase 14: Meeting Memory Ledger
**Goal**: Turn recorded call sessions into local full-session transcript ledgers with speaker/timing metadata and reviewable summaries.
**Depends on**: v1.2 session ledgers, v1.3 speaker suggestions
**Requirements**: MEM-01, MEM-02, MEM-03
**Success Criteria** (what must be TRUE):
  1. A user can save/load a session transcript ledger with chronological
     segments, timestamps, confidence, source window, category, and speaker
     metadata.
  2. Retention/storage behavior is configurable per profile/session and reports
     the exact local ledger path.
  3. A user can render a concise session summary with questions, handoffs,
     action items, and incomplete coverage.
  4. Existing sessions without full transcript data remain listable and report
     missing coverage instead of failing.
**Plans**: 4 plans

Plans:
- [x] 14-01: Add transcript ledger contracts and storage helpers
- [x] 14-02: Wire capture/session data into full-session ledgers
- [x] 14-03: Add retention config and local path diagnostics
- [x] 14-04: Add session summary rendering and tests

### Phase 15: Meeting Ask And Search
**Goal**: Let the user search local meeting sessions and ask questions about current or past sessions with cited transcript evidence.
**Depends on**: Phase 14
**Requirements**: ASK-01, ASK-02, ASK-03
**Success Criteria** (what must be TRUE):
  1. A user can search sessions by profile, session id, date range, speaker
     label, trigger category, and keyword.
  2. A user can ask a question about a current or selected past session and
     receive an answer with transcript-segment citations.
  3. Sanitized exports omit raw audio, secrets, and private config values.
  4. Search and ask commands handle partial or empty ledgers with clear
     diagnostics.
**Plans**: 3 plans

Plans:
- [x] 15-01: Add local meeting search filters and result rendering
- [x] 15-02: Add cited meeting-ask command and retrieval flow
- [x] 15-03: Add sanitized summary export and edge-case diagnostics

### Phase 16: Grounded Answer Drafts
**Goal**: Draft answers for addressed-question events using cited meeting memory and configured source-plugin context.
**Depends on**: Phase 15
**Requirements**: ANS-01, ANS-02, ANS-03
**Success Criteria** (what must be TRUE):
  1. A user can generate an answer draft from an addressed-question event and
     see citations to meeting-memory evidence.
  2. Jira, Confluence, Obsidian, and file source context can be included through
     existing config/plugin paths without hardcoded private names.
  3. Draft output reports source freshness, missing-source diagnostics, trigger
     evidence, and draft confidence before any action is taken.
  4. Existing prepare/speak flows continue to work without meeting-memory
     sources configured.
**Plans**: 4 plans

Plans:
- [x] 16-01: Add answer draft contracts with evidence and citations
- [x] 16-02: Assemble meeting-memory context for draft generation
- [x] 16-03: Add configured source-plugin context and freshness diagnostics
- [x] 16-04: Wire local composer drafting and fallback behavior

### Phase 17: Answer Cockpit And Audit Trail
**Goal**: Provide a live control surface that shows trigger evidence and a draft, requires explicit user action, and records an audit trail.
**Depends on**: Phase 16
**Requirements**: COCK-01, COCK-02, AUD-01, AUD-02
**Success Criteria** (what must be TRUE):
  1. A user can open a live cockpit view showing the current handoff candidate,
     trigger evidence, draft, citations, confidence, and actions.
  2. A user can choose speak, edit, skip, or takeover from cockpit or
     hotkey-compatible CLI actions.
  3. Saymo never auto-speaks an unapproved generated draft by default.
  4. A user can inspect/replay sanitized audit evidence for trigger decisions,
     generated drafts, selected actions, and spoken responses.
**Plans**: 4 plans

Plans:
- [x] 17-01: Add cockpit state model and command output
- [x] 17-02: Add speak/edit/skip/takeover action handling
- [x] 17-03: Add local audit trail for trigger/draft/action/speech events
- [x] 17-04: Add sanitized replay/report flow and safety tests

## Progress

**Execution Order:**
Phases execute in numeric order: 14 -> 15 -> 16 -> 17

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 14. Meeting Memory Ledger | v1.4 | 4/4 | Complete | 2026-05-20 |
| 15. Meeting Ask And Search | v1.4 | 3/3 | Complete | 2026-05-20 |
| 16. Grounded Answer Drafts | v1.4 | 4/4 | Complete | 2026-05-20 |
| 17. Answer Cockpit And Audit Trail | v1.4 | 4/4 | Complete | 2026-05-20 |

## Requirement Coverage

| Requirement | Phase |
|-------------|-------|
| MEM-01 | Phase 14 |
| MEM-02 | Phase 14 |
| MEM-03 | Phase 14 |
| ASK-01 | Phase 15 |
| ASK-02 | Phase 15 |
| ASK-03 | Phase 15 |
| ANS-01 | Phase 16 |
| ANS-02 | Phase 16 |
| ANS-03 | Phase 16 |
| COCK-01 | Phase 17 |
| COCK-02 | Phase 17 |
| AUD-01 | Phase 17 |
| AUD-02 | Phase 17 |

**Coverage:** 13/13 requirements mapped.
