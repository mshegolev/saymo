---
phase: 51
slug: dry-run-evidence-and-rehearsal-feedback
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-10
---

# Phase 51 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pyproject.toml`; no dedicated pytest config detected |
| **Quick run command** | `uv run pytest tests/analysis/test_launch_evidence.py tests/test_dry_run_cli.py tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~2s focused, full suite depends on local machine |

---

## Sampling Rate

- **After every task commit:** Run the task-specific `<automated>` command from the active PLAN.
- **After every plan wave:** Run `uv run pytest tests/analysis/test_launch_evidence.py tests/test_dry_run_cli.py tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py -q`
- **Before `$gsd-verify-work`:** Run `uv run pytest -q`
- **Max feedback latency:** 60 seconds for focused commands.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 51-01-01 | 01 | 1 | EVID-01, EVID-03 | RED unit/CLI | `uv run pytest tests/analysis/test_launch_evidence.py tests/test_dry_run_cli.py -q` | W0 creates `tests/analysis/test_launch_evidence.py` | pending |
| 51-01-02 | 01 | 1 | EVID-02 | RED CLI/integration | `uv run pytest tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q` | existing files extended | pending |
| 51-02-01 | 02 | 2 | EVID-01, EVID-03 | GREEN unit/CLI | `uv run pytest tests/analysis/test_launch_evidence.py tests/test_dry_run_cli.py -q` | yes after 51-01 | pending |
| 51-02-02 | 02 | 2 | EVID-02 | GREEN CLI/integration | `uv run pytest tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py -q` | yes after 51-01 | pending |

---

## Wave 0 Requirements

- [ ] `tests/analysis/test_launch_evidence.py` - new compare/load/redaction test file for EVID-01 and EVID-03.
- [ ] Extend `tests/test_dry_run_cli.py` - dry-run artifact completeness, `dry-run-compare`, and static no-mutation guard.
- [ ] Extend `tests/test_rehearsal_cli.py` - `--launch-json` recording and missing/invalid warning behavior.
- [ ] Extend `tests/test_session_scorecard_cli.py` - dry-run mode launch artifact acceptance and rehearsal fallback.
- [ ] Extend `tests/test_safety_soak_cli.py` - dry-run launch evidence gates through scorecard metrics.

---

## Manual-Only Verifications

All phase behaviors have automated verification. No manual synthesis, playback, recording, provider, launchd, or protected asset verification is required for Phase 51.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all MISSING references.
- [x] No watch-mode flags.
- [x] Feedback latency target < 60s for focused commands.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending execution
