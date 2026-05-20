---
phase: 08
slug: capture-session-ledger
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-20
---

# Phase 8 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_capture.py tests/analysis/test_trigger_sessions.py tests/test_trigger_check.py` |
| Full suite command | `.venv/bin/python -m pytest -q -k 'not qwen3_compute_loss'` |
| Estimated runtime | ~3 seconds |

## Per-Task Verification Map

| Task ID | Plan | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01 | 08-01 | SES-01, SES-02 | unit | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_sessions.py tests/analysis/test_trigger_capture.py` | yes | green |
| 08-02 | 08-02 | SES-01, SES-02 | CLI/unit | `.venv/bin/python -m pytest -q tests/analysis/test_trigger_capture.py tests/test_trigger_check.py` | yes | green |
| 08-03 | 08-03 | SES-02, SES-03 | CLI | `.venv/bin/python -m pytest -q tests/test_trigger_check.py` | yes | green |

## Wave 0 Requirements

Existing pytest infrastructure covers all Phase 8 requirements.

## Manual-Only Verifications

All Phase 8 behaviors have automated verification.

## Validation Sign-Off

- [x] All tasks have automated verification.
- [x] Sampling continuity has no unverified task gap.
- [x] Wave 0 dependencies already exist.
- [x] No watch-mode flags are required.
- [x] `nyquist_compliant: true` set in frontmatter.

Approval: approved 2026-05-20
