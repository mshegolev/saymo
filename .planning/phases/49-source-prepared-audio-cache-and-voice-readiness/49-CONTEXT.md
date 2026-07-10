# Phase 49: Source, Prepared Audio, Cache, And Voice Readiness - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase extends the existing `saymo dry-run` readiness path so the operator
can verify source data, prepared standup audio, response-cache coverage, and
cloned-voice readiness before a real call. It may create only the selected
Obsidian daily note through an explicit source-prepare flag, and all audio,
cache, voice, model, and training repairs must remain explicit operator
commands.

</domain>

<decisions>
## Implementation Decisions

### Source Note Handling
- Keep plain `saymo dry-run` read-only; it verifies the selected daily note
  but does not create or overwrite source files.
- Add an explicit source-only repair flag for dry-run, preferred as
  `--prepare-source`, that creates a missing selected Obsidian daily note
  without overwriting existing note content.
- Preserve `saymo call-ready --prepare` behavior for backward compatibility.
- Dry-run source remediation should point back to dry-run with the explicit
  source flag, not to automatic cache rebuilds.

### Prepared Audio Diagnostics
- Reuse existing prepared-audio sidecar and voice-cache metadata checks rather
  than adding a second metadata format.
- Show whether the prepared WAV matches the selected source hash, voice
  profile, profile approval state, and F5 `prepared` source-type preset
  metadata.
- Missing or stale prepared audio should produce a targeted
  `saymo prepare -p <profile>` repair command.
- Do not synthesize, delete, rotate, or overwrite prepared audio from dry-run.

### Response Cache Diagnostics
- Reuse existing response-cache coverage and staleness checks with
  source-aware F5 `response_cache` metadata.
- Surface coverage counts, missing/stale examples, source type, resolved preset
  metadata, and expensive F5 warnings without raw prompt or response text.
- Missing or stale response-cache variants should produce
  `saymo prepare-responses -p <profile>` guidance and must not add `--force`
  by default.
- Dry-run should not rebuild response-cache variants.

### Voice Readiness Safety
- Verify the selected cloned voice profile, approval status, engine safety, and
  stale metadata through existing selector/cache metadata helpers.
- Diagnostics must not read, copy, delete, retrain, or mutate training datasets,
  voice samples, model checkpoints, or fallback model assets.
- Keep private paths and fingerprints sanitized to the level already used by
  launch readiness and cache-status outputs.
- If voice metadata is stale or unapproved, explain the explicit review or
  prepare commands instead of changing the profile automatically.

### Claude's Discretion
- Choose the smallest collector parameterization that lets `call-ready` keep
  its current labels while `dry-run` emits dry-run-specific action and rerun
  commands.
- Add tests at the CLI and launch-readiness layer before implementation, then
  adjust production code only enough to satisfy the Phase 49 success criteria.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.commands.dry_run` already registers `saymo dry-run`, calls
  `collect_launch_readiness(..., prepare=False)`, and renders with
  `label="dry-run"`.
- `saymo.analysis.launch_sources.collect_daily_note_checks` already knows how
  to create a missing daily note when `prepare=True`, using
  `ensure_daily_note` without overwriting existing content.
- `saymo.analysis.launch_sources.prepared_audio_status` already compares the
  prepared WAV sidecar to source SHA256 and voice-cache metadata with
  `source_type="prepared"`.
- `saymo.analysis.launch_cache.collect_response_cache_check` and
  `response_cache_advice` already compute response-cache coverage and
  source-aware `response_cache` metadata.
- `saymo.analysis.launch_cache.collect_voice_metadata_check` already checks the
  live-call selector, clone status, profile approval, and safe metadata fields.

### Established Patterns
- Readiness checks return `LaunchReadinessCheck` objects with `status`,
  `detail`, `action`, `rerun`, and sanitized `metadata`.
- CLI tests use `CliRunner`, temporary YAML config files, monkeypatching of
  readiness collectors, and static guards for forbidden dry-run imports/actions.
- Cache and voice metadata tests assert sanitized source-type preset fields such
  as `source_type`, `purpose`, and resolved F5 preset identifiers.
- Repair guidance is textual; expensive F5 regeneration requires explicit
  operator commands.

### Integration Points
- `saymo.commands.dry_run` can expose the explicit source creation flag and
  pass a read-only or source-create intent into `collect_launch_readiness`.
- `saymo.analysis.launch_readiness.collect_launch_readiness` can carry a small
  caller context to source/cache collectors so dry-run and call-ready remediation
  labels remain correct.
- Tests belong in `tests/test_dry_run_cli.py`,
  `tests/analysis/test_launch_readiness.py`,
  `tests/analysis/test_cache_advice.py`, and
  `tests/analysis/test_response_cache.py` as needed.

</code_context>

<specifics>
## Specific Ideas

- The operator path should answer "why is it not ready?" with a command the
  user can copy, especially `saymo prepare -p <profile>` and
  `saymo prepare-responses -p <profile>`.
- The user previously warned that voice models and training datasets are
  expensive to recreate; this phase must keep those assets untouched unless a
  separate explicit command is run.
- Existing Phase 48 safety remains locked: no realtime start, no playback, no
  TTS synthesis, no provider mutation, no automatic cache repair.

</specifics>

<deferred>
## Deferred Ideas

- Phase 50 handles provider tab, Chrome state, BlackHole routing, playback and
  capture devices, call-control daemon, and LaunchAgent health.
- Phase 51 handles sanitized dry-run evidence reuse in rehearsal, scorecards,
  safety-soak, and latest-vs-previous readiness comparisons.
- Automatic prepared/cache rebuilds, force regeneration, voice retraining, and
  provider auto-repair remain out of scope.

</deferred>
