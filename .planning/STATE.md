---
gsd_state_version: 1.0
milestone: v1.13
milestone_name: F5 Prosody Metrics
current_phase: 47 of 47
current_phase_name: Source-Type Pause Presets
current_plan: 3
status: executing
stopped_at: Completed 47-02-PLAN.md
last_updated: "2026-07-09T20:44:31.844Z"
last_activity: 2026-07-09 - Completed Phase 47 Plan 02; Phase 47 is ready to execute Plan 03.
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 8
  completed_plans: 7
  percent: 88
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-09)

**Core value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.
**Current focus:** Phase 47: Source-Type Pause Presets.

## Current Position

Current Phase: 47 of 47
Current Phase Name: Source-Type Pause Presets
Current Plan: 3
Total Plans in Phase: 3
Plans: 47-01-PLAN.md, 47-02-PLAN.md, 47-03-PLAN.md
Status: Ready to execute
Last Activity: 2026-07-09 - Completed Phase 47 Plan 02; Phase 47 is ready to execute Plan 03.

Progress: [#########-] 88%

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 45 P01 | 3 min | 2 tasks | 4 files |
| Phase 45 P02 | 5 min | 2 tasks | 3 files |
| Phase 45 P03 | 2 min | 2 tasks | 3 files |
| Phase 46 P01 | 4 min | 2 tasks | 5 files |
| Phase 46 P02 | 4 min | 2 tasks | 4 files |
| Phase 47 P01 | 5 min | 2 tasks | 6 files |
| Phase 47 P02 | 9 min | 2 tasks | 13 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v1.10: Silent breath pauses replace audible breath splices for F5 live-call
  pacing.
- v1.10: F5 pacing knobs participate in voice-cache fingerprints so prepared
  and response cached WAVs go stale after timing changes.
- v1.11: Direct F5 cache-staleness, continuation-silence, and static/docs
  guards are the contract for preserving silent-breath behavior.
- v1.12: Focus on repeatable operator tuning and metadata-safe cache/review
  flows, not retraining or adding audible breath.
- v1.13: Focus on richer F5 preview coverage, objective timing metrics, and
  source-type preset selection around the existing approved F5 voice path.
- [Phase 45]: Corpus inspection CLI lists only ids, categories, and labels; phrase text remains API-only for later preview synthesis.
- [Phase 45]: Preview items share one writer path so manual labels and filenames stay backward-compatible while corpus previews add stable corpus-derived labels.
- [Phase 45]: Corpus preview artifacts expose only source_kind plus corpus id/category/label; raw phrase text remains limited to synthesis and hash/char-count inputs.
- [Phase 45]: Repeatable F5 timing tuning docs point operators to built-in corpus selections first; manual text is documented as one-off local preview.
- [Phase 45]: Final artifact regression treats manifest.json, review.json, and timing-report.md as the persisted privacy boundary for raw source text.
- [Phase 46]: F5 preview metrics are numeric summaries only: duration, measured duration when available, spoken counts, rate fields, and grouped pause totals.
- [Phase 46]: Pause accounting reuses the existing F5 natural-pacing splitter so comma handling and clause markers stay aligned with live synthesis.
- [Phase 46]: Dry-run rate comparisons use estimated duration, while non-dry-run records use measured WAV duration when supplied.
- [Phase 46]: Timing reports render numeric metadata only: display duration, chars/sec, words/minute, and grouped pause counts/seconds.
- [Phase 46]: Current-vs-candidate deltas use candidate minus current, with measured audio duration preferred over estimated duration when present.
- [Phase 46]: Phase 46 docs and code stay limited to metrics/report evidence; no source-type routing, cache behavior, or preset recommendation logic was added.
- [Phase 47]: Source-type overrides live under meetings.<profile>.voice.f5_pause_presets and never rewrite global F5 timing.
- [Phase 47]: Preset resolution falls back from source override to profile f5_pause_preset to global tts.f5tts.pause_preset.
- [Phase 47]: Source-type F5 fingerprinting resolves presets on a copied config so metadata changes never mutate loaded runtime config.
- [Phase 47]: Reviewed prepared audio reuses preserved source_profile for preset fingerprinting so review saves keep the prepare-time source context.
- [Phase 47]: prepare-responses now accepts -p/--profile and defaults to standup for backward-compatible response-cache metadata.

### Pending Todos

- Execute Phase 47 Plan 03: Sanitized cache-status/readiness diagnostics and operator docs.
- Deferred manual check: run one non-dry-run F5 corpus preview and listen to
  current/candidate WAVs when the operator explicitly wants to touch local
  approved F5 model assets.

### Blockers/Concerns

- Diagnostics and artifacts must stay sanitized: no prompt text, response text,
  audio bytes, raw transcripts, private meeting content, or secrets.
- Existing `.saymo` training data, model checkpoints, prepared audio, and
  response caches are protected local assets; v1.13 should inspect and test
  behavior without destructive cleanup.
- The F5 live-call path must keep `load_breath_sample()` out of synthesis and
  stitching.

## Session Continuity

Last session: 2026-07-09T20:44:31.842Z
Stopped at: Completed 47-02-PLAN.md
Resume file: None
