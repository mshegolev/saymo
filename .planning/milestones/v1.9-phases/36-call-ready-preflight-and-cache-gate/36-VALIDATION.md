---
phase: 36
slug: call-ready-preflight-and-cache-gate
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-08
---

# Phase 36 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | none - pytest is declared in `pyproject.toml` dev dependency group |
| **Quick run command** | `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/scripts/test_ensure_obsidian_daily_note.py tests/analysis/test_response_cache.py -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~60 seconds for focused suite; full suite runtime depends on local ML/audio skips |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
- **After every plan wave:** Run `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/analysis/test_response_cache.py tests/analysis/test_cache_metadata.py tests/scripts/test_ensure_obsidian_daily_note.py tests/test_trigger_check.py -q`
- **Before `$gsd-verify-work`:** `uv run pytest` must be green, or any environment-only skips/failures must be documented with exact output.
- **Max feedback latency:** 90 seconds for focused checks.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 0 | LAUN-01 | CLI stub | `uv run pytest tests/test_call_ready_cli.py::test_call_ready_prints_top_level_result -q` | No - W0 | pending |
| 36-01-02 | 01 | 1 | LAUN-01, LAUN-07 | unit + CLI | `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q` | No - W0 | pending |
| 36-02-01 | 02 | 0 | LAUN-02, LAUN-03 | unit | `uv run pytest tests/scripts/test_ensure_obsidian_daily_note.py tests/analysis/test_launch_readiness.py::test_placeholder_daily_note_blocks_source_readiness -q` | Partial - W0 | pending |
| 36-02-02 | 02 | 1 | LAUN-04 | unit | `uv run pytest tests/analysis/test_launch_readiness.py::test_prepared_audio_requires_current_metadata_and_source_digest -q` | No - W0 | pending |
| 36-03-01 | 03 | 1 | LAUN-05 | unit | `uv run pytest tests/analysis/test_response_cache.py::test_response_cache_coverage_reports_missing_and_stale_variants -q` | Partial | pending |
| 36-03-02 | 03 | 1 | LAUN-06 | unit + CLI | `uv run pytest tests/analysis/test_launch_readiness.py::test_voice_metadata_is_sanitized_and_actionable -q` | No - W0 | pending |
| 36-04-01 | 04 | 1 | LAUN-07 | CLI | `uv run pytest tests/test_call_ready_cli.py::test_call_ready_groups_remediation_with_rerun_commands -q` | No - W0 | pending |
| 36-04-02 | 04 | 2 | LAUN-01..LAUN-07 | integration | `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/analysis/test_response_cache.py tests/analysis/test_cache_metadata.py tests/scripts/test_ensure_obsidian_daily_note.py tests/test_trigger_check.py -q` | Mixed | pending |

*Status: pending -> green/red/flaky is updated by execution summaries.*

---

## Wave 0 Requirements

- [ ] `tests/analysis/test_launch_readiness.py` - stubs and failing tests for LAUN-03, LAUN-04, LAUN-06, and readiness report policy.
- [ ] `tests/test_call_ready_cli.py` - stubs and failing tests for LAUN-01, LAUN-02 CLI integration, LAUN-07 rendering, `--prepare`, and JSON output if implemented.
- [ ] `tests/analysis/test_response_cache.py` - extend public coverage helper tests for LAUN-05.
- [ ] `tests/scripts/test_ensure_obsidian_daily_note.py` or `tests/obsidian/test_daily_notes.py` - preserve existing note content and verify package-helper delegation.
- [ ] `tests/analysis/test_cache_metadata.py` - add source digest or stale-source metadata tests if the metadata schema is extended.

---

## Manual-Only Verifications

All Phase 36 launch-gate behaviors have automated verification. Live provider,
BlackHole route, Chrome tab, daemon, realtime loop, and evidence soak behavior
are intentionally deferred to Phases 37-40.

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 90s for focused checks
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-08
