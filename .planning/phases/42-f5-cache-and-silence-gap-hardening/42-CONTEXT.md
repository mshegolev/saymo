# Phase 42: F5 Cache and Silence Gap Hardening - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the remaining v1.11 F5 silent-breath hardening gaps without changing the
approved voice model, deleting local caches, or retuning subjective pause
durations. This phase is about regression coverage, cache-invalidating
contracts, static guards, and documentation clarity.

</domain>

<decisions>
## Implementation Decisions

### Cache Staleness
- Use existing `build_voice_cache_metadata()` and `check_voice_cache_metadata()`
  APIs; do not add a second fingerprint path.
- Prove both `prepare` and `response_cache` purposes go stale after F5 pacing
  knob changes.
- Diagnostics should stay stable and privacy-safe: use reason strings such as
  `voice_metadata_stale`, not prompt text, response text, audio bytes, or raw
  meeting content.

### F5 Silence Boundary
- Treat F5 breath behavior as timing-only silence for live-call output.
- Add explicit coverage for the `breath_interval_sentences` continuation branch,
  not only paragraph breaks.
- Keep `load_breath_sample()` available for non-F5 naturalness helpers but
  guarded out of `saymo/tts/f5tts.py`.

### Documentation
- Make `docs/VOICE-NATURALNESS.md` distinguish non-F5 audible breath splicing
  from F5 live-call silent timing.
- Keep config examples aligned with the runtime knobs already in
  `F5TTSConfig`.

### Claude's Discretion
- Choose the smallest test locations that match existing patterns.
- Add static tests instead of new runtime commands unless a current CLI path
  already needs code changes.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.analysis.cache_metadata` already reads/writes privacy-safe sidecars
  and returns `voice_metadata_stale`.
- `saymo.analysis.response_cache.response_cache_coverage()` already reports
  stale variants as stable `intent[idx]:reason` entries.
- `tests/tts/test_f5tts.py` uses a fake F5 engine with deterministic sample
  values and sample rate.
- `tests/test_realtime_static_guards.py` already keeps privacy and mutation
  static checks in one place.

### Established Patterns
- Cache metadata tests use `tmp_path` sidecars and avoid real audio synthesis.
- Response-cache tests use tiny local libraries and async fake synthesizers.
- F5 audio tests assert sample windows with `numpy.testing.assert_allclose`.
- Static privacy guards read source files as text and assert forbidden names are
  absent.

### Integration Points
- Prepared audio: `saymo.commands.core._prepare()` writes prepare metadata;
  `_call_ready_cached_audio()` and launch sources check it.
- Response cache: `ResponseCache.build()` writes metadata and coverage/readiness
  checks use `check_voice_cache_metadata()`.
- F5 runtime: `F5TTSCloneTTS._synthesize_natural_sync()` materializes silence
  around spoken chunks.

</code_context>

<specifics>
## Specific Ideas

- Add direct prepare and response-cache tests that build metadata before a knob
  change, then change `silent_breath_pause_seconds`, `sentence_pause_seconds`,
  `clause_pause_seconds`, and `breath_interval_sentences`.
- Add a continuation test for text with three adjacent sentences and
  `breath_interval_sentences = 2`.
- Add static docs/config tests proving the F5 live-call wording says silent
  timing, not audible breath injection.

</specifics>

<deferred>
## Deferred Ideas

- Named per-profile F5 pause presets.
- Automated A/B benchmark report for old/new pacing.
- Operator-facing warning before expensive cache regeneration.

</deferred>
