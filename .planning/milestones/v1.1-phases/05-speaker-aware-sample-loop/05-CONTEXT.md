# Phase 5 Context: Speaker-Aware Sample Loop

## Goal

Let the user label who spoke in captured windows and evaluate trigger behavior
separately for `me`, `other`, and `unknown` speakers.

## Current Baseline

- `trigger-capture` saves WAV plus JSON metadata under
  `~/.saymo/trigger_samples/<profile>/<category>/`.
- `trigger-samples list|replay|report` can inspect saved samples.
- `trigger-eval` re-runs deterministic trigger/addressing classification and
  reports stored/current categories, misses, and false positives.
- Sample metadata does not currently record who spoke.

## Decisions

- Do not add a required diarization dependency in this phase.
- Store speaker labels in the existing sample JSON metadata, defaulting to
  `unknown` for both new and old samples.
- Restrict speaker labels to `me`, `other`, and `unknown` so evaluation output
  stays stable and easy to compare.

