# Phase 34 Context: Call-ready Engine Selector and Fallback Chain

**Created:** 2026-07-07

## Goal

Let runtime synthesis use only approved voice profile engines and explicit
fallbacks while preserving existing prepare, cache, handbrake, and provider
safety behavior.

## Findings

- `saymo.tts.factory.get_tts_engine()` is the current central TTS dispatch.
- `prepare`, `prepare-responses`, `speak` cache-miss synthesis, approved draft
  playback, and auto live fallback already flow through this dispatch or small
  direct call sites.
- Prepared standup audio and response-cache WAVs have no metadata sidecars.
- Voice profile manifests already store reference hashes and
  `approved_for_calls`, but asset readiness is not the same as call approval.
- Existing handbrake, confirmation, addressing, stop, max-duration, and
  provider gates live outside TTS selection and must remain outside it.

## Implementation Boundary

- Add selector contracts behind factory/helper APIs.
- Do not change existing trigger/handbrake decision order.
- Do not delete or rewrite voice/model/training assets.
- Do not install packages or download model weights.
- Treat non-cloned engines as visible fallbacks but blocked for live-call output
  unless explicitly allowed.
