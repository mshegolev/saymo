---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Live Control Handbrake
status: roadmap ready; next phase 23
stopped_at: milestone v1.6 roadmap created; next step is $gsd-plan-phase 23.
last_updated: "2026-05-22"
last_activity: "2026-05-22 - created milestone v1.6 roadmap"
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 15
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.
**Current focus:** v1.6 Live Control Handbrake.

## Current Position

Phase: None
Plan: None
Status: Roadmap ready
Last activity: 2026-05-22 - created v1.6 roadmap with phases 23-26.

Progress: [----------] 0%

## Performance Metrics

**Current Milestone Velocity:**
- Total plans planned: 15
- Plans completed: 0
- Average duration: pending
- Total execution time: pending

**Historical Velocity:**
- v1.0 completed 11 plans across 4 phases.
- v1.1 completed 9 plans across 3 phases.
- v1.2 completed 11 plans across 3 phases.
- v1.3 completed 10 plans across 3 phases.
- v1.4 completed 15 plans across 4 phases.
- v1.5 completed 18 plans across 5 phases.

**By Phase:**

| Phase | Plans | Total | Status |
|-------|-------|-------|--------|
| 23. Operator Guide And Control Vocabulary | 3 | 0/3 | pending |
| 24. Runtime Handbrake State | 4 | 0/4 | pending |
| 25. Local Control Surface | 4 | 0/4 | pending |
| 26. macOS Hotkey Doctor And Safety Regression | 4 | 0/4 | pending |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting future work:

- v1.4: Generated answer drafts stay pending until explicit cockpit action.
- v1.5: Real captured sessions should become regression fixtures, but raw
  audio and transcripts stay local and are not committed.
- v1.5: Approved generated drafts may play only after an explicit user action
  and existing playback safety checks pass.
- v1.6: The handbrake is an explicit local safety boundary; when auto-answer
  is off or manual takeover is active, Saymo must not speak automatically.

### Pending Todos

Plan Phase 23.

### Blockers/Concerns

- Optional diarization backends may require large model downloads, GPU/MPS
  tuning, or external license/token acceptance.
- Manual speaker labels must stay authoritative over inferred suggestions.
- Real-time diarization remains out of scope until offline session suggestions
  prove reliable.
- Answer drafts must not become automatic live speaking without explicit user
  approval.
- Global macOS hotkeys require a running local Saymo listener process and
  Accessibility permission; terminal focus should not be required once the
  listener is active.
- Stored transcripts and summaries must stay local, configurable, and
  sanitizable.
- Real captured sessions can be used as local regression fixtures, but raw
  audio/transcripts must not be committed.

## Session Continuity

Last session: 2026-05-21
Stopped at: milestone v1.6 roadmap created; next step is `$gsd-plan-phase 23`.
Resume file: None
