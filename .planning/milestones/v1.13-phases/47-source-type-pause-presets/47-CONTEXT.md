# Phase 47: Source-Type Pause Presets - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 47 lets users choose F5 pause presets by answer source while preserving
the existing profile-level preset fallback and voice-cache safety. It should
cover prepared standup audio, response-cache variants, and spontaneous approved
answers. It must not retrain models, regenerate caches automatically, add
audible breath/noise, or change non-F5 engines.

</domain>

<decisions>
## Implementation Decisions

### Source-Type Model
- Use a small explicit source-type vocabulary for F5 pause preset overrides:
  `prepared`, `response_cache`, and `spontaneous`.
- Map source types to existing selector/cache purposes as follows:
  `prepared` -> `prepare`, `response_cache` -> `response_cache`,
  `spontaneous` -> `preview` for approved-answer preview/playback style
  generation unless a more specific existing purpose is already used.
- Keep profile-level `meetings.<profile>.voice.f5_pause_preset` as the fallback
  when no source-type override exists.
- Persist normal operator changes through CLI commands, not by asking the user
  to edit YAML manually.

### Config and CLI
- Add source-type override config under the meeting profile voice block rather
  than global private names, for example:
  `meetings.standup.voice.f5_pause_presets.prepared: calm`.
- Extend `saymo f5-presets apply` with an optional `--source-type` argument.
  Without `--source-type`, preserve the existing profile/global apply behavior.
- Add read-only display of active source-type preset resolution where useful,
  but avoid a separate UI beyond CLI output and diagnostics.
- Validate unknown source types and unknown preset ids with actionable errors.

### Fingerprint and Cache Safety
- Ensure source-type preset resolution affects the F5 engine fingerprint for
  the relevant purpose so prepared audio and response-cache metadata become
  stale after a source-type timing change.
- Preserve existing metadata checks: stale artifacts should report stable
  sanitized reasons such as `voice_metadata_stale`; do not include prompt text,
  response text, private meeting content, raw audio, or secrets.
- Do not rebuild caches automatically. Diagnostics should show targeted
  regeneration or review commands only.
- Existing profile-level preset behavior must remain backward-compatible when
  no source-type override is configured.

### Diagnostics
- `saymo cache-status -p <profile>` should show enough sanitized preset context
  to answer: which profile preset is active, which source-type override applies
  to prepared audio and response cache, and what command repairs stale
  artifacts.
- `saymo review -p <profile>` metadata writes must preserve source fields and
  use the same prepared/source-type preset fingerprint as prepare-time audio.
- Readiness/preflight diagnostics that already consume cache metadata should
  naturally see stale metadata through the fingerprint; add explicit preset
  details only where there is an existing safe detail surface.

### Claude's Discretion
- Choose helper function names and exact metadata keys, provided tests cover
  fallback behavior, source-type override behavior, cache staleness, and
  sanitized diagnostics.
- Keep source-type logic local and simple; avoid a general policy engine.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `F5TTSConfig` in `saymo/config.py` stores global F5 pause preset and concrete
  timing knobs used by the fingerprint payload.
- `saymo/commands/voice_clone.py` already implements `saymo f5-presets apply`
  and writes `meetings.<profile>.voice.f5_pause_preset`.
- `saymo/tts/f5_presets.py` applies named presets to `SaymoConfig` or
  `F5TTSConfig`, and `f5_timing_snapshot()` exposes privacy-safe timing
  fields.
- `selector_fingerprint_payload()` and `_engine_config_payload()` in
  `saymo/tts/selector.py` drive `VoiceCacheMetadata.fingerprint`.
- `build_voice_cache_metadata()` and `check_voice_cache_metadata()` in
  `saymo/analysis/cache_metadata.py` are the source of stale metadata checks.
- `prepared_audio_cache_advice()` and `response_cache_advice()` in
  `saymo/analysis/cache_advice.py` power `saymo cache-status`.
- `_write_reviewed_audio_cache()` in `saymo/commands/core.py` already writes
  current prepared-audio metadata after `saymo review`.

### Established Patterns
- Cache diagnostics are read-only and should warn about expensive F5
  regeneration rather than rebuilding anything.
- Cache metadata stores selector/purpose fingerprints and source hashes, not
  private source text.
- Tests around cache status and review metadata use temporary configs, temp
  audio files, and sidecar metadata.
- Existing source metadata fields (`source_kind`, `source_profile`,
  `source_sha256`) must be preserved by review paths.

### Integration Points
- Add source-type preset resolution near F5 preset helpers so selector,
  cache metadata, prepare/review, and CLI apply all use the same rules.
- Apply source-type timing to a copied/transient config for fingerprint
  payloads; avoid permanently mutating the loaded config outside explicit
  apply commands.
- Extend cache advice metadata/rendering with safe preset fields, then surface
  them in `cache-status`.
- Update `config.example.yaml`, `docs/voice-clone-shootout.md`, and
  `docs/VOICE-NATURALNESS.md` with the source-type override syntax and
  safety boundary.

</code_context>

<specifics>
## Specific Ideas

Suggested CLI:

```bash
saymo f5-presets apply calm --profile standup --source-type prepared
saymo f5-presets apply crisp --profile standup --source-type response_cache
saymo f5-presets apply deliberate --profile standup --source-type spontaneous
```

Suggested YAML:

```yaml
meetings:
  standup:
    voice:
      f5_pause_preset: calm
      f5_pause_presets:
        prepared: calm
        response_cache: crisp
        spontaneous: deliberate
```

</specifics>

<deferred>
## Deferred Ideas

- Automatic preset recommendations from Phase 46 metrics and preference
  reviews are deferred to future naturalness automation.
- Real cache regeneration/listening is deferred to explicit user commands.
- New source types beyond `prepared`, `response_cache`, and `spontaneous` are
  deferred until a real workflow needs them.

</deferred>
