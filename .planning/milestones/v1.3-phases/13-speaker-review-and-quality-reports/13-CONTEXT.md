# Phase 13 Context: Speaker Review And Quality Reports

## Goal

Let the user inspect, accept, reject, or override diarization speaker
suggestions before those suggestions affect trigger training data.

## Requirements

- SPKR-03: review, accept, reject, or override suggested speaker labels without
  losing the original diarization suggestion.
- QUAL-01: report speaker-label quality by session with unknown coverage,
  accepted suggestion counts, confidence buckets, and manual-vs-suggested
  conflicts.
- QUAL-02: trigger evaluation/readiness must keep manual speaker labels
  authoritative over unreviewed suggestions.
- QUAL-03: export sanitized diarization/speaker-review reports without raw
  audio payloads, transcript text, or private config values.

## Existing State

- Phase 11 added disabled-by-default diarization config and backend diagnostics.
- Phase 12 added session diarization sidecars under
  `<samples>/<profile>/_sessions/<session>.diarization.json`.
- Sidecars store backend-neutral speaker segments, speaker-id mappings, and
  per-sample suggestions.
- `trigger-sessions map-speaker` updates sidecar mappings and suggestion labels
  but does not mutate sample JSON.
- `trigger-eval`, classifier training, and readiness currently read sample JSON
  records only, which already prevents unreviewed sidecars from affecting
  training.

## Decisions

- Keep sample JSON `speaker` as the authoritative training/evaluation label.
- Keep original suggestion data in the sidecar. Review actions add status and
  reviewed label metadata instead of overwriting the suggestion itself.
- Applying a suggestion is explicit: accept and override may update sample JSON;
  reject only updates sidecar review metadata.
- Reports must be local and sanitized: no transcript text, no audio payloads, no
  config secrets, and no token/env values.

## Risks

- Sample JSON can move between category directories after diarization. Matching
  should tolerate moved paths by using session sequence and sample filename when
  needed.
- Unknown suggestions should not be silently accepted as useful speaker labels.
- Existing tests assert output snippets, so CLI additions should avoid breaking
  current output shape.
