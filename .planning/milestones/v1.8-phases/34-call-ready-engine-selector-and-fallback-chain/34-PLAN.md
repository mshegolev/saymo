# Phase 34 Plan: Call-ready Engine Selector and Fallback Chain

**Created:** 2026-07-07
**Status:** Ready for execution

## Goal

Let runtime synthesis use only approved voice profile engines and explicit
fallbacks while preserving existing prepare, cache, handbrake, and provider
safety behavior.

## Requirements Covered

RUN-01, RUN-02, RUN-03, RUN-04, RUN-05

## Plan 34-01: Selector Config and Decision Contracts

**Files:**
- `saymo/config.py`
- `saymo/tts/selector.py`
- `tests/test_config.py`
- `tests/tts/test_selector.py`

**Steps:**
1. Add purpose-specific selector config for preview, prepare, response cache,
   realtime, and live call.
2. Add selector decision data with selected engine, attempted engines,
   cloned/non-cloned status, blocked reason, profile approval, and reference
   fingerprint.
3. Keep absent config passive and backwards-compatible.

## Plan 34-02: Factory-backed Selector Resolution

**Files:**
- `saymo/tts/factory.py`
- `saymo/tts/selector.py`
- `tests/tts/test_factory.py`
- `tests/tts/test_selector.py`

**Steps:**
1. Expose engine instantiation by explicit engine key.
2. Resolve candidate fallback chains without importing unknown engines.
3. Block live-call non-cloned fallback unless explicitly allowed.

## Plan 34-03: Cache Metadata Sidecars

**Files:**
- `saymo/analysis/cache_metadata.py`
- `saymo/analysis/response_cache.py`
- `tests/analysis/test_cache_metadata.py`
- `tests/analysis/test_response_cache.py`

**Steps:**
1. Write privacy-safe `<audio>.meta.json` sidecars containing selector and
   voice-reference fingerprints.
2. Treat missing or stale metadata as invalid for call-ready cache reads.
3. Keep text/transcript content out of sidecars.

## Plan 34-04: Runtime Wiring

**Files:**
- `saymo/commands/core.py`
- `saymo/commands/__init__.py`
- `saymo/commands/tests.py`
- `tests/test_auto_qa_flow.py`

**Steps:**
1. Route prepare and response-cache synthesis through selector metadata.
2. Route speak, approved draft playback, and auto live fallback through
   selector checks.
3. Preserve existing handbrake, confirmation, provider, stop, and timeout
   gates outside selector logic.

## Plan 34-05: Documentation and State

**Files:**
- `docs/voice-clone-shootout.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`

**Steps:**
1. Document selector defaults, blocked reasons, and cache sidecars.
2. Mark RUN requirements complete only after focused and full tests pass.

## Verification Commands

```bash
uv run pytest tests/tts/test_selector.py tests/analysis/test_cache_metadata.py tests/analysis/test_response_cache.py tests/tts/test_factory.py tests/test_config.py tests/test_auto_qa_flow.py
uv run pytest -q
```
