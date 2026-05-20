# v1.3 Research: Architecture

## Existing Integration Points

- `saymo.analysis.trigger_sessions` owns capture-session ledgers and summaries.
- `saymo.analysis.trigger_review` owns review filters, relabeling, and
  sanitized reports.
- `saymo.analysis.trigger_readiness` and `trigger_classifier` consume speaker
  labels for readiness/evaluation.
- `saymo.commands.tests` currently hosts trigger-capture, trigger-sessions,
  trigger-samples, and trigger-classifier CLI surfaces.

## Proposed Components

- `saymo.analysis.diarization`
  - backend-neutral segment/result dataclasses
  - availability diagnostics
  - sidecar path helpers
  - suggestion merge helpers
- `saymo.analysis.diarization_pyannote`
  - optional import adapter
  - only loaded when configured/requested
- CLI additions
  - `saymo diarization-check`
  - `saymo trigger-sessions diarize`
  - `saymo trigger-sessions speakers`
  - speaker suggestion actions in `trigger-samples review`

## Data Flow

1. User records a session with `trigger-capture --session`.
2. User runs session diarization for that session.
3. Saymo writes session sidecars with raw speaker segments and per-sample
   speaker suggestions.
4. User reviews suggestions and promotes accepted labels into existing sample
   metadata.
5. Evaluation/readiness reads manual labels first and treats unaccepted
   suggestions as diagnostics only.

## Build Order

1. Optional config and adapter contracts.
2. Session-level diarization output and sidecars.
3. Review/promotion and quality reporting.
