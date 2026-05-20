# Phase 8 Context: Capture Session Ledger

## Goal

Treat every trigger-capture run as a named local session so training samples
from one meeting can be reviewed, summarized, and audited together.

## Baseline

- `saymo trigger-capture` already records fixed audio windows, classifies each
  window, and writes WAV plus JSON metadata under
  `~/.saymo/trigger_samples/<profile>/<category>/`.
- Sample metadata already records profile, category, trigger/addressing flags,
  speaker label, answer decision, transcript, and audio levels.
- `trigger-samples list/replay/report`, `trigger-eval`, and
  `trigger-classifier train` iterate existing JSON files and must keep working
  with old samples that have no session fields.

## Decisions

- Add session metadata without changing the existing category-based sample
  directory layout.
- Store session ledgers under
  `~/.saymo/trigger_samples/<profile>/_sessions/<session_id>.json`.
- Generate a stable session id from the user-provided session name plus the
  capture start timestamp; default the session name to the profile.
- Write `session_id`, `session_name`, and `session_sequence` into every saved
  sample JSON.
- Print and persist a summary when capture finishes normally or is stopped with
  Ctrl+C.
- Keep readiness in Phase 8 deliberately basic: enough saved samples plus both
  accepted/rejected labels. Phase 10 owns full classifier readiness gates.

