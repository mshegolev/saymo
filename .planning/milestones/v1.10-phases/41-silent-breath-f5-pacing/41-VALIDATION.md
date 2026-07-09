---
phase: 41
slug: silent-breath-f5-pacing
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-09
requirements: [F5P-01, F5P-02, F5P-03, F5P-04, F5P-05]
---

# Phase 41 - Validation Strategy

## Goal-Backward Truths

Phase 41 is complete only when all of these are true:

1. F5 natural pacing never transmits reference-sample breath audio into live
   microphone output.
2. Sentence, clause, paragraph, and continuation pauses are represented as
   configurable silence around spoken F5 chunks.
3. F5 pacing knobs are part of selector/cache fingerprints so prepared and
   response cached WAVs go stale when pause behavior changes.
4. Tests prove the zero-valued silence behavior and cache fingerprint
   invalidation.
5. A local F5 preview exists for ear-based timing review.

## Automated Validation Commands

### Focused F5 Natural Pacing Suite

```bash
uv run pytest \
  tests/tts/test_f5tts.py \
  tests/tts/test_selector.py \
  tests/tts/test_naturalness.py \
  tests/test_config.py \
  tests/analysis/test_cache_metadata.py \
  -q
```

### Full Suite

```bash
uv run pytest -q
```

### Whitespace Guard

```bash
git diff --check
```

## Required Test Coverage

| Requirement | Required Evidence | Status |
|-------------|-------------------|--------|
| F5P-01 | F5 stitching path contains no audible breath sample import/call and uses zero-valued silence for breath pauses. | green |
| F5P-02 | Sentence and clause pauses remain in natural pacing output. | green |
| F5P-03 | `silent_breath_pause_seconds` is configurable and included in cache fingerprint payload. | green |
| F5P-04 | Regression tests prove zero-valued breath silence and F5 pacing fingerprint invalidation. | green |
| F5P-05 | Preview WAV exists at `~/.saymo/voice_benchmarks/20260709-silent-breath/f5tts-silent-breath-01.wav`. | green |

## Latest Verification

| Command | Result |
|---------|--------|
| `uv run pytest tests/tts/test_selector.py::test_f5tts_pacing_config_changes_selector_fingerprint_payload -q` | RED before fix, then 1 passed |
| `uv run pytest tests/tts/test_selector.py tests/analysis/test_cache_metadata.py -q` | 10 passed |
| `uv run pytest tests/tts/test_selector.py tests/tts/test_f5tts.py tests/tts/test_naturalness.py tests/test_config.py tests/analysis/test_cache_metadata.py -q` | 42 passed |
| `uv run pytest -q` | 552 passed |
| `git diff --check` | passed |

## Manual Review

Listen with:

```bash
afplay ~/.saymo/voice_benchmarks/20260709-silent-breath/f5tts-silent-breath-01.wav
```

Ear-based timing approval remains subjective; timing can be tuned through
`sentence_pause_seconds`, `clause_pause_seconds`, and
`silent_breath_pause_seconds` without retraining.
