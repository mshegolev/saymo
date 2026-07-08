# Phase 32 Plan: Benchmark Scoring and F5 Baseline

**Created:** 2026-07-07
**Status:** Ready for execution

## Goal

Produce comparable, scored F5 baseline evidence before evaluating or promoting
any challenger engine.

## Requirements Covered

BEN-01, BEN-02, BEN-03, BEN-04, BEN-05

## Plan 32-01: Benchmark Artifact Contracts

**Files:**
- `saymo/analysis/voice_benchmark.py`
- `tests/analysis/test_voice_benchmark.py`

**Steps:**
1. Write failing tests for review template, score report rendering, status
   classification, and transcript redaction.
2. Implement additive artifact helpers for manifest/review/report.
3. Keep helpers independent from real TTS engines.

## Plan 32-02: Harness Integration

**Files:**
- `scripts/voice_clone_benchmark.py`
- `tests/scripts/test_voice_clone_benchmark.py`

**Steps:**
1. Write failing tests that dry-run output contains `review.json` and
   `score-report.md`.
2. Wire `write_outputs` to artifact helpers.
3. Preserve current manifest fields and blind-review behavior.

## Plan 32-03: Baseline Gate Semantics

**Files:**
- `saymo/analysis/voice_benchmark.py`
- `tests/analysis/test_voice_benchmark.py`

**Steps:**
1. Add tests that unscored reports are not promotion-ready.
2. Add tests that complete scored runs can be marked approved/rejected.
3. Ensure partial runs remain useful but not approved.

## Plan 32-04: Docs and Verification

**Files:**
- `docs/voice-clone-shootout.md`
- `.planning/*`

**Steps:**
1. Document `review.json` and `score-report.md`.
2. Run focused benchmark tests and full suite.
3. Update Phase 32 summary, verification, roadmap, requirements, state.

## Verification Commands

```bash
uv run pytest tests/analysis/test_voice_benchmark.py tests/scripts/test_voice_clone_benchmark.py
uv run pytest
```
