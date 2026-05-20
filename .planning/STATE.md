---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Live Conversation Memory + Answer Cockpit
status: Roadmap ready
stopped_at: Phase 14 complete; next step is Phase 15 Meeting Ask And Search.
last_updated: "2026-05-20"
last_activity: "2026-05-20 - completed Phase 14 Meeting Memory Ledger"
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 15
  completed_plans: 4
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-20)

**Core value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.
**Current focus:** v1.4 Live Conversation Memory + Answer Cockpit.

## Current Position

Phase: 15 Meeting Ask And Search
Plan: —
Status: Ready to plan Phase 15
Last activity: 2026-05-20 - Phase 14 added transcript ledgers, retention
config, local path diagnostics, and session summary output.

Progress: [###-------] 25%

## Performance Metrics

**Current Milestone Velocity:**
- Total plans planned: 15
- Plans completed: 4
- Average duration: pending
- Total execution time: pending

**Historical Velocity:**
- v1.0 completed 11 plans across 4 phases.
- v1.1 completed 9 plans across 3 phases.
- v1.2 completed 11 plans across 3 phases.
- v1.3 completed 10 plans across 3 phases.

**By Phase:**

| Phase | Plans | Total | Status |
|-------|-------|-------|--------|
| 14. Meeting Memory Ledger | 4 | 4/4 | complete |
| 15. Meeting Ask And Search | 3 | 0/3 | not started |
| 16. Grounded Answer Drafts | 4 | 0/4 | not started |
| 17. Answer Cockpit And Audit Trail | 4 | 0/4 | not started |

**Recent Trend:**
- v1.2 created reviewable sessions and corrected sample labels.
- v1.3 added optional diarization diagnostics, session sidecars, reviewable
  suggestion promotion, and sanitized speaker-quality reporting.

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v1.1: Use local speaker-label sidecars before requiring any diarization
  engine.
- v1.2: Treat capture runs as named local sessions so training samples can be
  reviewed in meeting context.
- v1.2: Keep review/relabel workflows local and CLI-first to avoid manual JSON
  edits.
- v1.2: Keep deterministic trigger/addressing checks as the live-call safety
  boundary; learned assist can only downgrade an answer candidate.
- v1.3: Diarization must be optional, disabled by default, and review-first.

### Pending Todos

- Start Phase 15 planning for local meeting search, cited meeting ask, and
  sanitized session export.

### Blockers/Concerns

- Optional diarization backends may require large model downloads, GPU/MPS
  tuning, or external license/token acceptance.
- Manual speaker labels must stay authoritative over inferred suggestions.
- Real-time diarization is intentionally out of scope until offline session
  suggestions prove reliable.
- Provider UI regression checks remain deferred beyond v1.3.
- Answer drafts must not become automatic live speaking without explicit user
  approval.
- Stored transcripts and summaries must stay local, configurable, and
  sanitizable.

## Session Continuity

Last session: 2026-05-20
Stopped at: Phase 14 complete; next step is Phase 15.
Resume file: None
