# Phase 34 Validation Strategy

**Created:** 2026-07-07

## Must Prove

- Purpose-specific selector config loads from YAML and preserves old defaults.
- Live-call output blocks missing/unapproved voice profiles and non-cloned
  engines by default.
- Explicit non-cloned live fallback approval is visible in selector metadata.
- Runtime synthesis still instantiates engines through the existing factory.
- Prepared and response-cache WAVs carry sidecar metadata and stale metadata is
  not silently accepted.
- Existing handbrake/confirmation/provider gates are not bypassed.

## Automated Coverage

- Selector unit tests for cloned, non-cloned, fallback, missing profile,
  unapproved profile, and approved profile cases.
- Cache metadata unit tests for write/read/stale/missing sidecars.
- Response cache tests for metadata-aware build and lookup.
- Factory/config tests for backwards compatibility.
- Auto Q&A tests for live-fallback selector blocked behavior.
