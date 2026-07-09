---
phase: 43
slug: f5-pause-presets-and-a-b-timing-review
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-09
requirements: [PAUSE-01, PAUSE-02, PAUSE-03, TUNE-01, TUNE-02, TUNE-03]
---

# Phase 43 - Validation Strategy

## Goal-Backward Truths

Phase 43 is complete only when all of these are true:

1. The operator can list named F5 pause presets and inspect their concrete
   timing values.
2. The operator can select/apply a named preset without hand-editing YAML.
3. Applied preset values are reflected in the existing F5 selector fingerprint
   path for cache invalidation.
4. A/B preview artifacts can compare current timing with a candidate preset.
5. A/B review artifacts can record preference and recommend a preset.
6. Preview/review artifacts remain sanitized and do not leak raw preview text,
   meeting transcript text, secrets, training data, or audio bytes.

## Automated Validation Commands

```bash
uv run pytest tests/test_config.py tests/tts/test_f5_presets.py tests/tts/test_selector.py tests/analysis/test_f5_timing_review.py tests/test_voice_clone_cli.py -q
```

```bash
uv run pytest -q
```

```bash
git diff --check
```
