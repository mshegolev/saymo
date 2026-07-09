---
phase: 42
slug: f5-cache-and-silence-gap-hardening
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-09
requirements: [F5G-01, F5G-02, F5G-03, F5G-04, F5G-05, F5G-06]
---

# Phase 42 - Validation Strategy

## Goal-Backward Truths

Phase 42 is complete only when all of these are true:

1. Prepared audio metadata created before an F5 pacing change becomes stale
   after any F5 pacing knob changes.
2. Response-cache metadata created before an F5 pacing change becomes stale
   after any F5 pacing knob changes.
3. Stale diagnostics expose stable reason strings and do not leak prompt text,
   response text, audio bytes, raw transcripts, private meeting content, or
   secrets.
4. Continuation pauses from `breath_interval_sentences` are zero-valued silence.
5. The F5 live-call path cannot import/call/splice `load_breath_sample()`.
6. Docs and config examples clearly state that F5 live-call breath behavior is
   silent timing only.

## Automated Validation Commands

```bash
uv run pytest \
  tests/analysis/test_cache_metadata.py \
  tests/analysis/test_response_cache.py \
  tests/tts/test_f5tts.py \
  tests/test_realtime_static_guards.py \
  -q
```

```bash
uv run pytest -q
```

```bash
git diff --check
```
