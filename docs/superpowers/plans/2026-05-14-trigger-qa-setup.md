# Trigger Q&A Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Saymo easier to configure for live-call triggers and safer at deciding whether a detected question is actually addressed to the user.

**Architecture:** Keep trigger matching deterministic and local by default. Add a small addressing classifier that consumes the same transcript window as `auto`, expose it through a `trigger-check` diagnostic command, and reuse it in `_auto()` to suppress obvious false positives. Keep response cache and live fallback unchanged.

**Tech Stack:** Python 3.11+, Click CLI, pytest, existing Saymo config dataclasses and response cache.

---

### Task 1: Addressing Classifier

**Files:**
- Create: `saymo/analysis/addressing.py`
- Test: `tests/analysis/test_addressing.py`

- [x] Write tests for direct questions, narrated mentions, generic team triggers, and empty text.
- [x] Implement `AddressingDecision` and `classify_addressing(transcript, trigger_phrases)`.
- [x] Verify with `pytest tests/analysis/test_addressing.py -q`.

### Task 2: Trigger Diagnostic CLI

**Files:**
- Modify: `saymo/commands/tests.py`
- Test: `tests/test_trigger_check.py`

- [x] Write tests for `saymo trigger-check --text ...` showing trigger, addressing, question, and cache status.
- [x] Add text-mode diagnostics first; add `--mic` as a best-effort transcription path using the existing input-device helper.
- [x] Verify with `pytest tests/test_trigger_check.py -q`.

### Task 3: Auto-Mode Guard

**Files:**
- Modify: `saymo/commands/core.py`
- Test: `tests/test_auto_qa_flow.py`

- [x] Write tests that non-addressed mentions fall back to silence/ignore and addressed questions still resolve.
- [x] In `_auto()`, call `classify_addressing()` on the transcript window and skip playback for `mentioned_not_addressed` or `ignore`.
- [x] Verify with focused auto/Q&A tests.

### Task 4: Setup Guidance and Roadmap

**Files:**
- Modify: `config.example.yaml`
- Modify: `docs/voice-identity.md`
- Modify: `docs/QUICK-START.md`

- [x] Document `trigger-check`, add config comments for fuzzy expansions, intent classifier, and confirmation/safety.
- [x] Update `voice-identity.md` to mark shipped hotkeys, timeout, response cache, and remaining trigger setup work accurately.
- [x] Verify docs mention real command names.

### Task 5: Final Verification

- [x] Run `bash -n setup.sh`.
- [x] Run focused pytest targets.
- [x] Run `.venv/bin/python -m pytest -q`.
- [x] Remove generated caches and commit.
