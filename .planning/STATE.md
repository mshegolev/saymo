---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Call-ready Voice Clone
status: milestone implementation complete
stopped_at: Phase 35 complete; next step is audit milestone v1.8.
last_updated: "2026-07-07"
last_activity: "2026-07-07 - completed Phase 35 preview approval and safety soak"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 22
  completed_plans: 22
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.
**Current focus:** v1.8 Call-ready Voice Clone.

## Current Position

Phase: milestone audit
Plan: None
Status: Phase 35 complete; next step is auditing milestone v1.8.
Last activity: 2026-07-07 - completed Phase 35 preview approval and safety soak.

Progress: [##########] 100%

## Performance Metrics

**Current Milestone Velocity:**
- Total plans planned: 22
- Plans completed: 22
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

| Phase | Status | Plans |
|-------|--------|-------|
| 31. Voice Asset Inventory and Profile Setup | Complete | 4/4 |
| 32. Benchmark Scoring and F5 Baseline | Complete | 4/4 |
| 33. Candidate Shootout Gates | Complete | 4/4 |
| 34. Call-ready Engine Selector and Fallback Chain | Complete | 5/5 |
| 35. Preview, A/B Approval, and Safety Soak | Complete | 5/5 |

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

### Pending Todos

Audit milestone v1.8 completion before archiving.

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
Stopped at: Phase 35 complete; next step is audit milestone v1.8.
Resume file: None
