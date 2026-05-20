# v1.3 Research: Pitfalls

## Dependency And Model Risk

- Diarization packages may be large, slow to install, or require model access
  steps. Prevent this by optional imports and clear diagnostics.
- Model/token configuration can leak secrets if copied into docs or reports.
  Prevent this by env interpolation and sanitized output.

## Product Risk

- Diarization does not identify "me" by itself; it usually produces anonymous
  speaker clusters. Prevent bad labels by requiring explicit mapping/review.
- Automatic overwrites would corrupt training data. Prevent this by sidecar
  suggestions and manual promotion.
- Live diarization can add latency and false confidence. Keep v1.3 offline and
  session-based.

## Integration Risk

- Existing trigger samples may have no session id or no adjacent audio. Keep
  legacy paths valid and report skipped samples.
- Session windows are short and may split speakers. Store confidence/conflict
  diagnostics instead of treating every segment as authoritative.
- Classifier readiness should not silently consume unreviewed suggestions.
  Manual labels must remain the source of truth.
