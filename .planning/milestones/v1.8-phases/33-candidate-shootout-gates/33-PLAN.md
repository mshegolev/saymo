# Phase 33 Plan: Candidate Shootout Gates

**Created:** 2026-07-07
**Status:** Ready for execution

## Goal

Evaluate Qwen3 Base and later candidates without accidental installs,
downloads, runtime promotion, or training.

## Requirements Covered

CAND-01, CAND-02, CAND-03, CAND-04, CAND-05

## Plan 33-01: Qwen3 Baseline Gate

**Files:**
- `scripts/voice_clone_benchmark.py`
- `saymo/analysis/voice_benchmark.py`
- `tests/scripts/test_voice_clone_benchmark.py`
- `tests/analysis/test_voice_benchmark.py`

**Steps:**
1. Add tests that Qwen dry-run does not require baseline report.
2. Add tests that real Qwen requires baseline score report and transcript.
3. Add score-report gate helper.
4. Wire helper into Qwen real-run path.

## Plan 33-02: Qwen3 Base vs Runtime Separation

**Files:**
- `scripts/voice_clone_benchmark.py`
- `docs/qwen3-base-voice-clone-notes.md`
- `docs/voice-clone-shootout.md`

**Steps:**
1. Add settings metadata distinguishing official Qwen3 Base benchmark from
   production `qwen3_clone`.
2. Document separation and promotion boundary.

## Plan 33-03: Later Candidate Blocks

**Files:**
- `docs/cosyvoice-voice-clone-notes.md`
- `docs/voice-clone-shootout.md`

**Steps:**
1. Document that CosyVoice/GPT-SoVITS/LoRA remain blocked until score reports
   justify opening the next gate.
2. Keep install commands as explicit future/user-approved actions.

## Plan 33-04: Internal PyPI Isolated Runtime Docs

**Files:**
- `docs/voice-clone-shootout.md`

**Steps:**
1. Add internal Nexus3 PyPI preference for approved isolated runtime installs.
2. State that the mirror is not hardcoded and not used for model weights.

## Verification Commands

```bash
uv run pytest tests/analysis/test_voice_benchmark.py tests/scripts/test_voice_clone_benchmark.py
uv run pytest
```
