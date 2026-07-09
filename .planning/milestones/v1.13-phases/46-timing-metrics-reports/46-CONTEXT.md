# Phase 46: Timing Metrics Reports - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 46 adds objective, privacy-safe timing metrics to the existing F5 timing
preview artifacts and reports. It builds on Phase 45 corpus previews and must
not add source-type preset routing, cache fingerprint changes, cache
regeneration behavior, or automatic preset recommendation.

</domain>

<decisions>
## Implementation Decisions

### Metrics Contract
- Add deterministic metrics that work for dry-run previews by analyzing the
  selected text through the same F5 natural-pacing preparation/splitting logic.
- Include total duration as `estimated_total_duration_seconds` for every
  record; when a real WAV exists, also include `audio_duration_seconds` and let
  the report display it as the measured duration.
- Include normalized rate fields suitable for comparing presets without raw
  text: at minimum `chars_per_second` and `words_per_minute`.
- Keep metrics scoped to numeric summaries; never persist raw manual text,
  corpus phrase text, prompt text, response text, audio bytes, private meeting
  content, secrets, voice samples, or training data.

### Pause Distribution
- Group pause metrics by `sentence`, `clause`, `paragraph`, and
  `silent_breath` to match v1.13 requirements.
- Reuse `prepare_for_natural_pacing()` and `split_for_tts()` from
  `saymo.tts.naturalness` so clause markers and explicit pauses are counted
  consistently with the F5 live-call path.
- Derive pause counts and seconds from the candidate F5 timing snapshot and
  the prepared chunks; this is acceptable for dry-run because no model output
  exists.
- Keep comma handling unchanged; do not add pauses after every comma.

### Report UX
- Extend `timing-report.md` with compact numeric columns or bullet lines that
  show duration, rate, and pause distribution for each clip.
- Add a current-vs-candidate comparison section that highlights sanitized
  deltas such as duration delta, rate delta, and pause total delta.
- Keep report readable in terminal and markdown without adding a UI or
  notebook dependency.
- Existing `review.json` and preference recording must remain backward
  compatible with older manifests that do not have metrics.

### Claude's Discretion
- Choose the exact helper module name and internal dataclasses, provided the
  public artifact shape is JSON-serializable and tests cover the numeric
  contract.
- Round numeric values consistently, preferably to two decimals for seconds and
  rates.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo/analysis/f5_timing_review.py` builds sanitized preview records,
  writes `manifest.json`, `review.json`, and `timing-report.md`, and renders
  the human-readable report.
- `saymo/commands/voice_clone.py` owns `_write_f5_preset_preview()`, which
  already knows the selected text, timing config, output WAV path, dry-run
  state, source kind, corpus id/category/label, and latency.
- `saymo/tts/naturalness.py` provides `prepare_for_natural_pacing()`,
  `split_for_tts()`, and pause token handling used by the F5 path.
- `saymo/tts/f5tts.py` materializes F5 natural pacing from spoken chunks plus
  zero-valued silence segments; its algorithm is the behavioral reference for
  pause accounting.
- `soundfile` is already a project dependency and is used elsewhere for WAV
  duration/audio loading.

### Established Patterns
- Preview artifacts store text hashes, character counts, timing snapshots,
  preset ids, artifact paths, and safe corpus metadata only.
- Dry-run preview must avoid model invocation while still writing useful
  artifacts.
- Tests use `CliRunner`, temp config, dry-run artifacts, and explicit
  assertions that raw source text is absent from `manifest.json`,
  `review.json`, and `timing-report.md`.
- F5 natural pacing uses silent pauses only; audible breath/noise must not be
  introduced.

### Integration Points
- Add metrics while building each record in `build_f5_timing_record()` or via
  a helper called by that function.
- If measured WAV duration is added, compute it in `_write_f5_preset_preview()`
  after writing non-dry-run audio and pass the numeric duration into the record
  builder.
- Extend `render_f5_timing_report()` to display per-clip metrics and
  current-vs-candidate deltas.
- Add tests in `tests/test_voice_clone_cli.py`; add a focused unit test file
  if a new metrics helper warrants direct coverage.

</code_context>

<specifics>
## Specific Ideas

Suggested artifact shape:

```json
"metrics": {
  "estimated_total_duration_seconds": 2.74,
  "audio_duration_seconds": null,
  "spoken_chars": 64,
  "spoken_words": 12,
  "chars_per_second": 23.36,
  "words_per_minute": 262.77,
  "pause_distribution": {
    "sentence": {"count": 1, "seconds": 0.38},
    "clause": {"count": 1, "seconds": 0.18},
    "paragraph": {"count": 0, "seconds": 0.0},
    "silent_breath": {"count": 0, "seconds": 0.0}
  }
}
```

Report should mention safe numeric metadata only, for example:
`duration=2.74s rate=23.36 chars/s pauses=sentence 0.38s, clause 0.18s`.

</specifics>

<deferred>
## Deferred Ideas

- Source-type preset routing and cache fingerprint behavior are deferred to
  Phase 47.
- Automatic preset recommendation from metrics plus preference history is
  deferred to future naturalness automation.
- Real listening validation for audio quality remains an operator action and
  is not required for dry-run metric correctness.

</deferred>
