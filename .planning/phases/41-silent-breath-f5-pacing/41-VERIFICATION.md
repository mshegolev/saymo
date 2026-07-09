---
phase: 41-silent-breath-f5-pacing
verified: 2026-07-09T08:50:00Z
status: passed
score: 5/5 must-haves verified
---

# Phase 41: Silent Breath F5 Pacing Verification Report

**Phase Goal:** Replace audible breath splices with configurable silent breath
pauses and prove generated F5 WAV output contains silence at breath points.
**Verified:** 2026-07-09T08:50:00Z
**Status:** passed

## Goal Achievement

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | F5 natural pacing no longer transmits reference-sample breath audio. | VERIFIED | `saymo/tts/f5tts.py` no longer imports or calls `load_breath_sample()` in the F5 stitching path. |
| 2 | Breath and paragraph points materialize as zero-valued silence. | VERIFIED | `test_f5tts_natural_pacing_uses_silent_breath_pause_for_paragraph_break` asserts the entire breath pause block is zero. |
| 3 | Sentence and clause pauses remain configurable. | VERIFIED | `F5TTSConfig` exposes `sentence_pause_seconds`, `clause_pause_seconds`, and `silent_breath_pause_seconds`; config loading test covers YAML overrides. |
| 4 | F5 natural pacing still batches spoken chunks once. | VERIFIED | `test_f5tts_natural_pacing_batches_spoken_chunks_once` forbids per-sentence CLI calls. |
| 5 | Real local preview exists for ear review. | VERIFIED | `~/.saymo/voice_benchmarks/20260709-silent-breath/f5tts-silent-breath-01.wav` generated successfully. |

## Requirements Coverage

| Requirement | Description | Status |
|-------------|-------------|--------|
| F5P-01 | Breath moments are silent pauses without hum/buzz/breath samples | SATISFIED |
| F5P-02 | Sentence and clause pauses remain while breath audio is disabled | SATISFIED |
| F5P-03 | Silent breath timing is configurable separately | SATISFIED |
| F5P-04 | Tests prove breath points are zero-valued silence | SATISFIED |
| F5P-05 | Local preview exists for ear-based review | SATISFIED |

## Automated Checks

| Command | Result |
|---------|--------|
| `uv run pytest tests/tts/test_f5tts.py::test_f5tts_natural_pacing_uses_silent_breath_pause_for_paragraph_break -q` | 1 passed after RED/GREEN cycle |
| `uv run pytest tests/tts/test_f5tts.py tests/tts/test_naturalness.py tests/test_config.py -q` | 32 passed |
| `uv run pytest tests/tts -q` | 64 passed |
| `uv run pytest -q` | 551 passed |
| `git diff --check` | passed |

## Manual Evidence

Preview path:

```bash
~/.saymo/voice_benchmarks/20260709-silent-breath/f5tts-silent-breath-01.wav
```

Playback command:

```bash
afplay ~/.saymo/voice_benchmarks/20260709-silent-breath/f5tts-silent-breath-01.wav
```

Preview metadata:

- sample rate: 24000
- duration: 2.81s
- peak: 0.7973
- longest quiet run: 0.753s
- size: 132 KB

## Residual Risk

Ear-based approval is still subjective. The implementation now removes the
audible breath/noise source; remaining tuning is pause duration only.

---
*Verified: 2026-07-09*
