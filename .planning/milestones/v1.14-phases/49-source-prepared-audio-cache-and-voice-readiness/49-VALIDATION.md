---
phase: 49
slug: source-prepared-audio-cache-and-voice-readiness
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-10
---

# Phase 49 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | none detected |
| **Quick run command** | `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~10 seconds targeted, full suite under 30 seconds based on Phase 48/47 history |

---

## Sampling Rate

- **After every task commit:** Run the quick command above or the task-specific subset in the PLAN.
- **After every plan wave:** Run `uv run pytest tests/test_dry_run_cli.py tests/test_call_ready_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py tests/analysis/test_cache_metadata.py tests/tts/test_selector.py -q`.
- **Before `$gsd-verify-work`:** Run `uv run pytest -q`.
- **Max feedback latency:** 60 seconds for focused tests.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 1 | SRC-01, SRC-03, CACHE-02, VOICE-01 | CLI RED | `uv run pytest tests/test_dry_run_cli.py -q` | yes | pending |
| 49-01-02 | 01 | 1 | SRC-01, SRC-02, SRC-03, CACHE-01, CACHE-02, VOICE-01 | unit RED | `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py -q` | yes | pending |
| 49-02-01 | 02 | 2 | SRC-01, SRC-02, SRC-03 | GREEN | `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py -q` | yes | pending |
| 49-02-02 | 02 | 2 | CACHE-01, CACHE-02, VOICE-01 | GREEN | `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py -q` | yes | pending |

*Status: pending until execution. Plan 49-01 intentionally produces RED failures before 49-02.*

---

## Wave 0 Requirements

- [ ] `tests/test_dry_run_cli.py` - add dry-run `--prepare-source`, dry-run collector context, targeted repair, and static safety contracts.
- [ ] `tests/analysis/test_launch_readiness.py` - add dry-run source creation, dry-run rerun/action, prepared metadata, and voice readiness contracts.
- [ ] `tests/analysis/test_cache_advice.py` - add no-default-force response-cache repair guidance regression.
- [ ] `tests/analysis/test_response_cache.py` - add source-aware response-cache coverage regression if existing coverage is too indirect.
- [x] pytest infrastructure exists.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | SRC-01, SRC-02, SRC-03, CACHE-01, CACHE-02, VOICE-01 | All Phase 49 behavior can be covered by CLI/unit tests with temp files and monkeypatches. | Not applicable |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing test references.
- [x] No watch-mode flags.
- [x] Feedback latency target < 60s for focused tests.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-07-10
