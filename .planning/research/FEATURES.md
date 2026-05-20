# v1.3 Research: Features

## Table Stakes

- Availability check: user sees whether the local diarization backend is
  configured and why it is unavailable.
- Session diarization: user runs diarization for a completed capture session by
  profile/session id.
- Speaker cluster summary: user sees speaker ids, sample counts, time ranges,
  confidence, and unresolved coverage.
- Speaker mapping: user maps backend speaker ids to Saymo's stable labels:
  `me`, `other`, `unknown`.
- Review flow: user accepts, rejects, or overrides suggestions before they
  influence training.

## Differentiators

- Suggestions are sidecar metadata, not automatic overwrites.
- Manual labels remain authoritative.
- Reports stay sanitized and omit transcript/audio payloads.
- Evaluation/readiness can distinguish manual labels from unreviewed
  suggestions.

## Anti-Features

- Do not require diarization dependencies for users who only need manual review.
- Do not add cloud diarization as the default.
- Do not run real-time diarization in `saymo auto` before offline results have
  been reviewed and measured.
