# Phase 2 Context: Catcher Tuning Loop

## Goal

Let the user tune live detection from config and validate those changes against
saved trigger samples.

## Existing Baseline

- `trigger-capture` already saved WAV plus JSON metadata under
  `~/.saymo/trigger_samples/<profile>/`.
- `trigger-setup` and `trigger-learn` could update
  `vocabulary.fuzzy_expansions`, but there was no offline evaluation loop.
- Capture window, overlap, cooldown, and silence threshold were not configurable
  per profile.

## Decisions

- Use the existing sample JSON as the offline evaluation substrate.
- Store profile-level live tuning under `meetings.<profile>.live`.
- Treat evaluated `asked_to_speak` samples that no longer answer as misses, and
  non-`asked_to_speak` samples that now answer as false positives.

