---
gsd_state_version: 1.0
milestone: v1.14
milestone_name: Call Dry-Run To Real Call
current_phase: Not started
current_phase_name: Defining requirements
current_plan: —
status: defining_requirements
stopped_at: Started v1.14 milestone
last_updated: "2026-07-10T00:00:00+04:00"
last_activity: 2026-07-10 - Started milestone v1.14 Call Dry-Run To Real Call.
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-09)

**Core value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.
**Current focus:** Milestone v1.14 Call Dry-Run To Real Call.

## Current Position

Current Phase: Not started
Current Phase Name: Defining requirements
Current Plan: —
Total Plans in Phase: —
Plans: —
Status: Defining requirements
Last Activity: 2026-07-10 - Started milestone v1.14 Call Dry-Run To Real Call.

Progress: [----------] 0%

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
| Phase 47 P03 | 6 min | 2 tasks | 9 files |

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
- [Phase 47]: Cache-status renders compact resolver-backed preset ids only: source_type, profile, override, and resolved.
- [Phase 47]: Response-cache diagnostics use profile-targeted saymo prepare-responses -p <profile> advice and keep --force only as an avoid-unless-intentional warning.
- [Phase 47]: Source-type preset docs explicitly exclude retraining, automatic cache rebuilding, audible breath/noise, cloud services, and automatic preset recommendations.

### Pending Todos

- Deferred manual check: run one non-dry-run F5 corpus preview and listen to
  current/candidate WAVs when the operator explicitly wants to touch local
  approved F5 model assets.
- Define requirements and roadmap for v1.14 Call Dry-Run To Real Call.

### Blockers/Concerns

- Diagnostics and artifacts must stay sanitized: no prompt text, response text,
  audio bytes, raw transcripts, private meeting content, or secrets.
- Existing `.saymo` training data, model checkpoints, prepared audio, and
  response caches are protected local assets; v1.13 should inspect and test
  behavior without destructive cleanup.
- The F5 live-call path must keep `load_breath_sample()` out of synthesis and
  stitching.

## Session Continuity

Last session: 2026-07-10T00:00:00+04:00
Stopped at: Started v1.14 milestone
Resume file: None
