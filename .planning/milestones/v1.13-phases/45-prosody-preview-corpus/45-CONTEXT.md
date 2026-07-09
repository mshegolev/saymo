# Phase 45: Prosody Preview Corpus - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 45 extends the existing `saymo f5-presets preview` flow so F5 timing
comparison can run against a richer built-in, sanitized corpus and selected
answer-shape subsets. It must not change source-type preset routing, timing
metrics, cache-status diagnostics, or real cache regeneration behavior; those
belong to later v1.13 phases.

</domain>

<decisions>
## Implementation Decisions

### Corpus Shape
- Provide a committed default corpus made only of synthetic, non-private
  phrases covering short acknowledgements, standup updates, multi-sentence
  answers, clause-heavy responses, and direct handoff replies.
- Store stable IDs, categories, labels, and text in code or package data so CLI
  output and tests can refer to exact corpus entries.
- Keep corpus text generic; do not derive entries from real meeting
  transcripts, prompts, prepared notes, voice samples, training datasets, or
  raw audio.
- Allow future custom corpora only through explicit local input paths if added
  later; this phase only needs the safe built-in corpus plus inspection.

### Preview Selection
- Add normal CLI controls to `saymo f5-presets preview` for choosing corpus
  entries or categories without requiring the operator to paste private text.
- Preserve the existing `--text` path for one-off manual previews, but make
  corpus-based preview the safer path for repeatable tuning.
- Generate current-vs-candidate clips for each selected corpus entry using the
  existing dry-run and synthesis flow.
- Keep output filenames and manifest records stable enough to tell which
  synthetic corpus entry produced each clip without writing the raw text into
  artifacts.

### Sanitized Artifacts
- Continue storing only hashes, character counts, timing snapshots, labels,
  preset IDs, and artifact paths in `manifest.json`, `review.json`, and
  `timing-report.md`.
- Add corpus metadata that is safe to reveal, such as `corpus_id`, category,
  and label; do not write phrase text into manifest, review, or report files.
- Tests must assert that private manual preview text and representative corpus
  phrase text are absent from committed preview artifacts.
- Keep dry-run useful: corpus preview in dry-run should write the same
  sanitized metadata and expected clip records without invoking F5.

### Claude's Discretion
- Choose the exact corpus module/file name and CLI option names, as long as
  they match existing Click style and stay discoverable in `--help`.
- Keep implementation small and local to the F5 preset preview path; avoid new
  dependencies.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo/commands/voice_clone.py` owns the `f5-presets` Click group, including
  `list`, `show`, `apply`, `preview`, and `review`.
- `_write_f5_preset_preview()` already builds current/candidate config pairs,
  synthesizes or dry-runs WAV paths, and calls
  `write_f5_timing_preview_artifacts()`.
- `saymo/analysis/f5_timing_review.py` already writes privacy-safe
  `manifest.json`, `review.json`, and `timing-report.md` using text hashes and
  character counts instead of raw text.
- `saymo/tts/f5_presets.py` contains the existing named timing presets and
  privacy-safe timing snapshot helper.
- `tests/test_voice_clone_cli.py` already has CLI coverage for preset
  list/show/apply plus sanitized dry-run preview/review artifacts.

### Established Patterns
- F5 tuning is config-only around the approved local `f5tts_clone` path; do
  not retrain or switch engines.
- CLI commands import heavier modules inside command functions to keep startup
  light.
- Preview and review artifacts are sanitized and must not store private text,
  prompt text, response text, audio bytes, secrets, or training data.
- Tests use `CliRunner`, temporary config files, dry-run preview, and explicit
  absence assertions for private text.

### Integration Points
- Add corpus resolution before `_write_f5_preset_preview()` loops over
  current/candidate configs.
- Extend `build_f5_timing_record()` and report rendering only with safe corpus
  metadata.
- Update docs that already describe `saymo f5-presets preview`, especially
  `docs/voice-clone-shootout.md` and `docs/VOICE-NATURALNESS.md`.
- Update `config.example.yaml` only if a new config key is introduced; prefer
  no new config for this phase.

</code_context>

<specifics>
## Specific Ideas

Use categories similar to:
- `acknowledgement`
- `standup`
- `multi_sentence`
- `clause_heavy`
- `handoff`

Suggested CLI shape:
- `saymo f5-presets corpus list`
- `saymo f5-presets preview calm --corpus standup --dry-run`
- `saymo f5-presets preview calm --corpus-id standup-blocked --dry-run`

</specifics>

<deferred>
## Deferred Ideas

- Automatic speech-rate and pause-distribution metrics are deferred to Phase
  46.
- Source-type preset routing and cache fingerprint changes are deferred to
  Phase 47.
- Automatic preset recommendation from metrics plus user preference history is
  deferred to future naturalness automation.

</deferred>
