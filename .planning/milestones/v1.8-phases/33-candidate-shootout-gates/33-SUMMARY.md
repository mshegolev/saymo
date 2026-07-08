# Phase 33 Summary: Candidate Shootout Gates

**Completed:** 2026-07-07
**Status:** Complete

## Delivered

- Added `require_completed_score_report()` in
  `saymo/analysis/voice_benchmark.py` for completed/scored baseline gates.
- Added `--baseline-report` to `scripts/voice_clone_benchmark.py`.
- Kept Qwen3 Base dry-run import/download free and baseline-report free.
- Made real Qwen3 Base generation fail fast before importing `qwen_tts` unless
  a completed/scored F5 baseline score report is provided.
- Added Qwen benchmark metadata that separates official `qwen_tts` Base
  evidence from production `qwen3_clone` runtime readiness.
- Documented that CosyVoice, GPT-SoVITS, LoRA, and installs remain gated until
  score evidence justifies opening the next step.
- Documented approved isolated runtime installs with internal Nexus3 PyPI
  preference, without hardcoding a mirror URL in project config.

## Verification

```bash
uv run pytest tests/analysis/test_voice_benchmark.py tests/scripts/test_voice_clone_benchmark.py
uv run pytest -q
```

Results:

- Focused: 13 passed.
- Full suite: 391 passed, 1 skipped.
