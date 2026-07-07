---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Call-ready Voice Clone
status: defining requirements
stopped_at: v1.8 started; next step is define requirements and roadmap.
last_updated: "2026-07-07"
last_activity: "2026-07-07 - started v1.8 Call-ready Voice Clone"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.
**Current focus:** v1.8 Call-ready Voice Clone.

## Current Position

Phase: None
Plan: None
Status: Defining requirements.
Last activity: 2026-07-07 - started Call-ready Voice Clone.

Progress: [----------] 0%

## Performance Metrics

**Current Milestone Velocity:**
- Total plans planned: 0
- Plans completed: 0
- Average duration: same-day execution
- Total execution time: same-day execution

**Historical Velocity:**
- v1.0 completed 11 plans across 4 phases.
- v1.1 completed 9 plans across 3 phases.
- v1.2 completed 11 plans across 3 phases.
- v1.3 completed 10 plans across 3 phases.
- v1.4 completed 15 plans across 4 phases.
- v1.5 completed 18 plans across 5 phases.
- v1.6 completed 16 plans across 4 phases.

**By Phase:**

No phases defined yet.

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
- v1.6: Global hotkeys and local button controls share one action catalog and
  audit path instead of separate hidden behavior.
- v1.7: Reliability work should combine real sessions and rehearsal runs
  without committing raw audio, transcripts, or local meeting content.
- v1.8: Voice-clone assets and training datasets are protected local state;
  default work should inventory and benchmark them without destructive changes.

### Pending Todos

Define v1.8 requirements and roadmap.

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
- Native menu bar app, LaunchAgent control listener, and voice-command
  handbrake remain future work.

## Session Continuity

Last session: 2026-07-07
Stopped at: v1.8 started; next step is requirements and roadmap.
Resume file: None
