# Phase 43: F5 Pause Presets and A/B Timing Review - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver operator-controlled F5 timing presets and A/B timing review for the
already-approved local `f5tts_clone` voice path. This phase covers listing
presets, selecting a preset per meeting profile, applying preset values to the
runtime F5 config, generating sanitized A/B preview artifacts, and recording
preference review output. It must not retrain models, switch providers, inject
audible breath/noise, mutate protected `.saymo` training assets, or rebuild real
response caches automatically.

</domain>

<decisions>
## Implementation Decisions

### Preset Model
- Use a small built-in preset catalog in source control, with stable preset IDs
  and explicit values for `sentence_pause_seconds`, `clause_pause_seconds`,
  `silent_breath_pause_seconds`, and `breath_interval_sentences`.
- Include the current v1.10/v1.11 timing as the default baseline preset so
  existing configs keep the same behavior.
- Add a `pause_preset` field to `F5TTSConfig`; applying a preset copies concrete
  timing values into the existing F5 config fields so the existing selector
  fingerprint path invalidates prepared and response caches.
- Allow per-meeting profile selection by writing
  `meetings.<profile>.voice.f5_pause_preset` plus concrete top-level F5 timing
  values. Runtime synthesis continues to use the existing top-level F5 config
  until profile-specific voice config is introduced in a later phase.

### Operator Commands
- Add a `saymo f5-presets` command group for list, show, apply, preview, and
  review actions. Keep output compact and CLI-native; no new UI.
- Apply is explicit and file-based: write only the selected config YAML, never
  real audio cache directories or training datasets.
- Default config target is the loaded config path when available; tests may pass
  `--config` and apply writes back to that file.

### A/B Timing Review
- Generate preview WAVs under `~/.saymo/voice_benchmarks/<run_id>/` by default,
  with `current.wav`, `<preset>.wav`, `manifest.json`, `review.json`, and
  `score-report.md`-style timing summary artifacts.
- Keep preview text sanitized: artifacts may store phrase IDs, preset IDs,
  timing values, output WAV paths, and text hashes, but never raw prompt text,
  meeting transcript text, secrets, or training data.
- A/B preview should use the approved local F5 selector purpose when real
  synthesis runs, but tests can exercise the artifact writer without invoking
  heavy F5 runtime.

### Claude's Discretion
- Choose exact preset values conservatively around the current approved timing.
- Reuse existing dataclass config patterns and voice benchmark artifact style
  instead of introducing a new dependency.
- Add focused tests before code and keep implementation small enough for Phase
  44 to harden cache UX separately.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `F5TTSConfig` already stores the F5 timing knobs that must be controlled.
- `selector_fingerprint_payload()` already includes F5 timing knobs in cache
  fingerprints, so applying concrete values is enough to invalidate old caches.
- `voice_benchmark.write_benchmark_artifacts()` establishes a privacy-safe
  artifact pattern with manifest/review/report files.
- `voice-preview` and `voice-profile` commands in `saymo/commands/voice_clone.py`
  show existing Click command style for voice operations.
- `tests/test_voice_clone_cli.py`, `tests/analysis/test_voice_benchmark.py`,
  and `tests/test_config.py` provide matching test patterns.

### Established Patterns
- Config is loaded from YAML into dataclasses via `_dict_to_dataclass()`.
- CLI tests use `CliRunner` with a temp `--config` file.
- Privacy tests assert private source text is absent from JSON/Markdown
  artifacts.
- Voice cache sidecars store hashes/fingerprints rather than raw source text.

### Integration Points
- New preset values connect through `SaymoConfig.tts.f5tts`.
- Cache invalidation remains through `selector_fingerprint_payload()` and
  `build_voice_cache_metadata()`.
- Preview/review commands connect under `saymo/commands/voice_clone.py`.
- Documentation/config examples connect through `config.example.yaml` and
  voice clone docs.

</code_context>

<specifics>
## Specific Ideas

- Start with preset IDs: `approved`, `calm`, `crisp`, and `deliberate`.
- `approved` should match the current defaults: sentence `0.38`, clause
  `0.18`, silent breath `0.6`, interval `2`.
- `crisp` should shorten gaps for faster live replies; `deliberate` should
  lengthen gaps for clearer human pacing.
- A/B review should prefer a simple JSON workflow first: operator fills or CLI
  records `preferred: current|candidate` plus notes, and the report shows the
  recommended preset.

</specifics>

<deferred>
## Deferred Ideas

- Automatic pause-distribution metrics.
- Separate runtime pause presets per source type.
- Richer phrase corpus for subjective voice evaluation.
- Profile-specific runtime F5 config resolution beyond persisting the meeting
  profile's selected preset name.

</deferred>
