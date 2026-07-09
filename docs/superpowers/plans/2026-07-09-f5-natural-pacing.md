# F5 Natural Pacing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add natural pauses and silent breath timing to F5-TTS output without retraining.

**Architecture:** Keep the public TTS API unchanged. Add conservative text prosody preparation in `saymo.tts.naturalness`, then make `F5TTSCloneTTS.synthesize()` optionally route through chunked synthesis and WAV stitching.

**Tech Stack:** Python 3.11+, pytest, numpy, soundfile, existing F5-TTS subprocess adapter.

---

### Task 1: Text Prosody Primer

**Files:**
- Modify: `saymo/tts/naturalness.py`
- Test: `tests/tts/test_naturalness.py`

- [x] Write failing tests for em dash, semicolon, non-time colon, and preserved commas.
- [x] Run `uv run pytest tests/tts/test_naturalness.py -q` and confirm RED.
- [x] Implement `prepare_for_natural_pacing()`.
- [x] Export the helper from `saymo.tts.naturalness`.
- [x] Run `uv run pytest tests/tts/test_naturalness.py -q` and confirm GREEN.

### Task 2: F5 Chunked Audio Stitching

**Files:**
- Modify: `saymo/tts/f5tts.py`
- Test: `tests/tts/test_f5tts.py`

- [x] Write failing tests that monkeypatch `_synthesize_sync()` and inspect the stitched WAV.
- [x] Run `uv run pytest tests/tts/test_f5tts.py -q` and confirm RED.
- [x] Implement natural pacing synthesis using existing `split_for_tts()` and silent breath pauses.
- [x] Keep a raw single-call fallback for disabled natural pacing.
- [x] Run `uv run pytest tests/tts/test_f5tts.py -q` and confirm GREEN.

### Task 3: Defaults And Docs

**Files:**
- Modify: `saymo/config.py`
- Modify: `config.example.yaml`
- Modify: `docs/VOICE-NATURALNESS.md`

- [x] Add F5 natural pacing defaults to `F5TTSConfig`.
- [x] Document conservative tuning knobs.
- [x] Run focused config and TTS tests.

### Task 4: Verification

**Files:**
- No source changes expected.

- [x] Run `uv run pytest tests/tts/test_naturalness.py tests/tts/test_f5tts.py tests/test_config.py -q`.
- [x] Run a short F5 preview if local F5 runtime is available.
- [x] Report the output WAV path and exact playback command.
