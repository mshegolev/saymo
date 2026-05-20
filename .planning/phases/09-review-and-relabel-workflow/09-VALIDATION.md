---
phase: 09
slug: review-and-relabel-workflow
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-20
---

# Phase 9 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_review.py tests/test_trigger_check.py` |
| Full suite command | `.venv/bin/python -m pytest -q -k 'not qwen3_compute_loss'` |
| Estimated runtime | ~3 seconds |

## Per-Task Verification Map

| Task ID | Plan | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01 | 09-01 | REV-01 | unit/CLI | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_review.py tests/test_trigger_check.py -k "filter or disagreement"` | yes | green |
| 09-02 | 09-02 | REV-02 | unit/CLI | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_review.py tests/test_trigger_check.py -k "category"` | yes | green |
| 09-03 | 09-03 | REV-03 | CLI | `.venv/bin/python -m pytest -q tests/test_trigger_check.py -k "review"` | yes | green |
| 09-04 | 09-04 | REV-04 | unit/CLI/docs | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_review.py tests/test_trigger_check.py -k "report"` | yes | green |

## Wave 0 Requirements

Existing pytest infrastructure covers all Phase 9 requirements.

## Manual-Only Verifications

All Phase 9 behaviors have automated verification.

## Validation Sign-Off

- [x] All tasks have automated verification.
- [x] Sampling continuity has no unverified task gap.
- [x] Wave 0 dependencies already exist.
- [x] No watch-mode flags are required.
- [x] `nyquist_compliant: true` set in frontmatter.

Approval: approved 2026-05-20
