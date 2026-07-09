---
phase: 44-cache-regeneration-and-review-metadata-safety
milestone: v1.12
status: planned
created: 2026-07-09
---

# Phase 44 Context: Cache Regeneration and Review Metadata Safety

## Goal

Make stale F5 cache state understandable and repairable without wasteful
regeneration, while ensuring review/regeneration paths keep the voice metadata
sidecars required by call-ready checks.

## Current Facts

- Prepared standup audio is written by `_prepare()` and `_prepare_team()` in
  `saymo/commands/core.py`.
- Prepared audio sidecars use `build_voice_cache_metadata(..., purpose="prepare")`
  and `write_voice_cache_metadata()`.
- `_call_ready_cached_audio()` already blocks live-call playback when the
  prepared WAV is missing, stale, or has no sidecar.
- `saymo review` currently writes the reviewed WAV over today's cache path but
  does not write or preserve the `.meta.json` sidecar.
- Response cache build already regenerates stale variants when metadata
  mismatches and `force=false`.
- `ResponseCache.lookup()` and `get_variant_by_key()` both use `_variant_ready()`;
  tests should lock that metadata behavior for both active and classifier paths.
- Current remediation text is too generic: it does not tell the user when F5
  regeneration can be expensive or which command rebuilds only prepared audio
  versus response variants.

## Decisions

1. Add a small `saymo.analysis.cache_advice` helper rather than scattering
   command-string logic across CLI modules.
2. Add `saymo cache-status -p <profile>` as a read-only diagnostic. It does not
   regenerate or delete anything.
3. Print explicit cost warnings only when a cache is missing/stale/partial and
   regeneration might be needed.
4. Prefer targeted commands:
   - prepared standup: `saymo prepare -p <profile>`
   - response cache: `saymo prepare-responses`
   - full response rebuild only when explicitly intended: `saymo prepare-responses --force`
5. Preserve existing prepared-audio sidecar source fields during `saymo review`
   when possible; otherwise write a new sanitized sidecar from the normalized
   reviewed text.
6. Keep diagnostics sanitized: stable status/reason strings, hashes, counts, and
   paths only; no prompt text, response text, transcript text, audio bytes, or
   secrets.

## Out of Scope

- No automatic deletion of real cache files.
- No automatic regeneration from `cache-status`, `auto-preflight`, or
  `call-ready`.
- No training/model asset changes.
- No audible breath/noise changes.

## Success Evidence

- Focused tests prove cost warnings and targeted commands for stale/missing
  prepared and response caches.
- Focused tests prove `saymo review` writes a current metadata sidecar after
  saving reviewed audio.
- Focused tests prove `lookup()` and `get_variant_by_key()` refuse stale
  response-cache WAVs when `voice_metadata` is configured.
- Full pytest remains green.
