# Phase 34 Summary: Call-ready Engine Selector and Fallback Chain

**Completed:** 2026-07-07
**Status:** Complete

## Delivered

- Added `voice_selector` config for preview, prepare, response cache, realtime,
  and live-call purposes.
- Added `saymo.tts.selector` decision contracts with selected engine, attempted
  fallback chain, cloned/non-cloned status, profile approval, reference hashes,
  and blocked reason.
- Added factory-backed selected engine creation without changing existing
  `get_tts_engine()` callers.
- Added privacy-safe voice cache sidecars in `saymo.analysis.cache_metadata`.
- Extended response cache build/lookup to use metadata when provided.
- Routed prepare, response-cache synthesis, speak cache-miss synthesis,
  approved draft playback, and auto live fallback through selector checks.
- Added call-ready cache checks before treating prepared WAVs as live-call
  output.
- Added auto-preflight visibility for voice selector and metadata-current
  response cache variants.
- Documented selector defaults and added `voice_selector` to
  `config.example.yaml`.

## Verification

```bash
uv run pytest tests/tts/test_selector.py tests/analysis/test_cache_metadata.py tests/analysis/test_response_cache.py tests/tts/test_factory.py tests/test_config.py tests/test_auto_qa_flow.py
uv run pytest tests/test_trigger_check.py tests/test_rehearsal_cli.py tests/analysis/test_remediation.py tests/test_safety_soak_cli.py tests/analysis/test_response_cache.py tests/test_auto_qa_flow.py
uv run pytest -q
```

Results:

- Focused selector/cache/config/auto: 102 passed.
- Preflight/remediation/auto related: 110 passed.
- Full suite: 402 passed, 1 skipped.
