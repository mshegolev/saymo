---
phase: 10
slug: classifier-readiness-gate
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-20
---

# Phase 10 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_readiness.py tests/analysis/test_trigger_classifier.py tests/test_trigger_check.py` |
| Full suite command | `.venv/bin/python -m pytest -q -k 'not qwen3_compute_loss'` |
| Estimated runtime | ~3 seconds |

## Per-Task Verification Map

| Task ID | Plan | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01 | 10-01 | CLS-01 | unit/CLI | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_readiness.py tests/test_trigger_check.py -k "readiness"` | yes | green |
| 10-02 | 10-02 | CLS-02 | unit/CLI | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_readiness.py tests/test_trigger_check.py -k "evaluate"` | yes | green |
| 10-03 | 10-03 | CLS-03 | unit/CLI/integration | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_readiness.py tests/test_trigger_check.py -k "live_assist"` | yes | green |
| 10-04 | 10-04 | CLS-04 | CLI/docs | `.venv/bin/python -m pytest -q tests/test_trigger_check.py -k "live_assist"` | yes | green |

## Wave 0 Requirements

Existing pytest infrastructure covers all Phase 10 requirements.

## Manual-Only Verifications

All Phase 10 behaviors have automated verification.

## Validation Sign-Off

- [x] All tasks have automated verification.
- [x] Sampling continuity has no unverified task gap.
- [x] Wave 0 dependencies already exist.
- [x] No watch-mode flags are required.
- [x] `nyquist_compliant: true` set in frontmatter.

Approval: approved 2026-05-20
