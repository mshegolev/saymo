---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Call Launch Readiness
status: defining requirements
stopped_at: v1.9 started from selected priorities: call launch readiness, realtime meeting loop, live-control daemon/menu bar.
last_updated: "2026-07-08"
last_activity: "2026-07-08 - started milestone v1.9 Call Launch Readiness"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-08)

**Core value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.
**Current focus:** Defining v1.9 Call Launch Readiness: one green pre-call path,
realtime loop readiness, and local daemon/control availability.

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements for milestone v1.9.
Last activity: 2026-07-08 - started milestone v1.9 Call Launch Readiness.

Progress: [----------] 0%

## Performance Metrics

**Current Milestone Velocity:**
- Total plans planned: 0
- Plans completed: 0
- Average duration: not started
- Total execution time: not started

**Historical Velocity:**
- v1.0 completed 11 plans across 4 phases.
- v1.1 completed 9 plans across 3 phases.
- v1.2 completed 11 plans across 3 phases.
- v1.3 completed 10 plans across 3 phases.
- v1.4 completed 15 plans across 4 phases.
- v1.5 completed 18 plans across 5 phases.
- v1.6 completed 16 plans across 4 phases.
- v1.7 completed 15 plans across 4 phases.
- v1.8 completed 22 plans across 5 phases.

**By Phase:**

| Phase | Status | Plans |
|-------|--------|-------|
| v1.9 phases | Pending roadmap | 0/0 |

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
- v1.8 Phase 31: Voice inventory/profile commands are read-only by default,
  profile writes require explicit `--apply`, and transcript text is not emitted
  in JSON/Markdown/profile manifests.
- v1.8 Phase 32: Every benchmark run writes `review.json` and
  `score-report.md`; partial or unscored runs are not promotion-ready.
- v1.8 Phase 33: Real Qwen3 Base generation requires a completed/scored F5
  baseline report before importing `qwen_tts`; dry-run remains import-free and
  official Base benchmark artifacts stay separate from production
  `qwen3_clone`.
- v1.8 Phase 34: Runtime synthesis now has purpose-specific selector
  decisions; live-call output blocks missing/unapproved profiles and
  non-cloned engines by default, and prepared/response-cache WAVs use
  privacy-safe metadata sidecars to detect stale voice/engine state.
- v1.8 Phase 35: Voice profiles can be approved/rejected only from completed
  scored benchmark evidence; preview audits are preview-only and text-safe;
  safety-soak fails on voice profile/cache/non-cloned live-call blockers.
- Post-v1.8: The `personal` F5 profile is approved from benchmark run
  `20260707-213256-f5tts`, and the active config uses `tts.engine:
  f5tts_clone`.
- v1.9: The selected priority order is call launch readiness, realtime meeting
  loop, then live-control daemon/menu bar.

### Pending Todos

Define v1.9 requirements and roadmap. First implementation should make the
current failure mode visible and actionable: missing prepared standup audio,
provider tab readiness, launchd helper health, and whether the call-control
listener is actually available before a meeting.

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
- Productized native menu bar packaging remains future work, but a local
  daemon/LaunchAgent control listener is now in v1.9 scope.

## Session Continuity

Last session: 2026-07-08
Stopped at: v1.9 new-milestone initialization.
Resume file: None
