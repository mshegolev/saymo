---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Local Diarization Assist
status: defining requirements and roadmap
stopped_at: v1.3 Local Diarization Assist roadmap ready; next step is plan Phase 11.
last_updated: "2026-05-20"
last_activity: "2026-05-20 - started v1.3 Local Diarization Assist milestone"
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 10
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-20)

**Core value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.
**Current focus:** Milestone v1.3 Local Diarization Assist.

## Current Position

Phase: 11 - Diarization Adapter And Config
Plan: Not started
Status: Requirements and roadmap defined
Last activity: 2026-05-20 - v1.3 milestone started from deferred local
diarization scope.

Progress: [----------] 0%

## Performance Metrics

**Current Milestone Velocity:**
- Total plans planned: 10
- Plans completed: 0
- Average duration: pending
- Total execution time: pending

**Historical Velocity:**
- v1.0 completed 11 plans across 4 phases.
- v1.1 completed 9 plans across 3 phases.
- v1.2 completed 11 plans across 3 phases.

**By Phase:**

| Phase | Plans | Total | Status |
|-------|-------|-------|--------|
| 11. Diarization Adapter And Config | 3 | 0/3 | not started |
| 12. Session Speaker Suggestions | 3 | 0/3 | not started |
| 13. Speaker Review And Quality Reports | 4 | 0/4 | not started |

**Recent Trend:**
- v1.2 created reviewable sessions and corrected sample labels.
- v1.3 now adds optional diarization suggestions on top of that review loop.

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

Plan and execute Phase 11: Diarization Adapter And Config.

### Blockers/Concerns

- Optional diarization backends may require large model downloads, GPU/MPS
  tuning, or external license/token acceptance.
- Manual speaker labels must stay authoritative over inferred suggestions.
- Real-time diarization is intentionally out of scope until offline session
  suggestions prove reliable.
- Provider UI regression checks remain deferred beyond v1.3.

## Session Continuity

Last session: 2026-05-20
Stopped at: v1.3 roadmap ready; next step is `$gsd-plan-phase 11`.
Resume file: None
