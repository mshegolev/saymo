# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-18)

**Core value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.
**Current focus:** No active milestone

## Current Position

Phase: —
Plan: —
Status: Archived
Last activity: 2026-05-19 — Archived milestone v1.1 Call Intelligence Loop

Progress: [██████████] 100%

## Performance Metrics

**Current Milestone Velocity:**
- Total plans completed: 9
- Average duration: autonomous batch
- Total execution time: one autonomous session

**Historical Velocity:**
- v1.0 completed 11 plans across 4 phases in one autonomous batch.

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 5. Speaker-Aware Sample Loop | 3 | 3/3 | autonomous |
| 6. Local Trigger Classifier | 3 | 3/3 | autonomous |
| 7. Provider Latency Probe | 3 | 3/3 | autonomous |

**Recent Trend:**
- Last 5 plans: 06-02, 06-03, 07-01, 07-02, 07-03
- Trend: milestone complete

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v1.0: Separate Speedly Catcher work from Speedly Sayer work so latency and
  quality regressions can be isolated.
- v1.0: Use captured call windows as the tuning substrate before adding any
  custom classifier.
- v1.0: Keep the sample report sanitized by omitting transcript text and raw
  audio payloads while still listing sample basenames and classification flags.
- v1.0: Treat response cache coverage as a preflight warning, not a hard block,
  because prepared standup fallback remains valid.
- v1.1: Use local speaker-label sidecars before requiring any diarization
  engine.
- v1.1: Keep learned trigger classifier behavior in shadow mode until there is
  enough accepted/rejected sample evidence.
- v1.1: Measure provider latency through existing provider abstractions instead
  of redesigning provider UI automation.
- v1.1 Phase 5: Speaker labels are stored in sample JSON metadata and restricted
  to `me`, `other`, and `unknown`.
- v1.1 Phase 6: Answer-decision labels are stored as `answer_decision`, and the
  local classifier remains shadow-only until enough evidence supports enabling
  it in live auto-mode.
- v1.1 refinement: plain name mentions are classified as `mentioned_me`, while
  direct questions and floor handoffs remain `asked_to_speak`.
- v1.1 Phase 7: Provider latency probes use existing Chrome provider
  abstractions and write JSON/Markdown history by profile/provider.

### Pending Todos

Start the next milestone with `$gsd-new-milestone`.

### Blockers/Concerns

- Need enough real captured samples in `~/.saymo/trigger_samples/` to make
  speaker-aware evaluation and classifier training meaningful.
- Local diarization remains optional; v1.1 must work without it.
- Classifier quality depends on accepted/rejected labels; low-label training is
  intentionally refused.
- Mention-vs-handoff heuristics need continued review against real saved
  samples before they should become learned live behavior.
- Provider latency history is only meaningful after probing real active calls.

## Session Continuity

Last session: 2026-05-18
Stopped at: v1.1 archived; next step is `$gsd-new-milestone`.
Resume file: None
