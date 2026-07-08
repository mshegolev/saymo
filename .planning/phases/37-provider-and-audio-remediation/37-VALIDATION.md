---
phase: 37
slug: provider-and-audio-remediation
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-08
---

# Phase 37 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | none - pytest is declared in `pyproject.toml` dev dependency group |
| **Quick run command** | `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~60 seconds for focused suite; full suite ~5 seconds locally |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
- **After every plan wave:** Run `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/test_hotkey_doctor.py tests/analysis/test_remediation.py -q`
- **Before `$gsd-verify-work`:** `uv run pytest` must be green.
- **Max feedback latency:** 90 seconds for focused checks.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 37-01-01 | 01 | 0 | PROV-01, PROV-05 | unit + CLI | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_provider_tab_readiness_reports_found_missing_and_errors tests/test_call_ready_cli.py::test_call_ready_includes_provider_tab_readiness -q` | No - W0 | pending |
| 37-01-02 | 01 | 1 | PROV-01 | unit + CLI | `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q` | No - W0 | pending |
| 37-02-01 | 02 | 1 | PROV-02 | unit | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_audio_route_checks_validate_expected_devices_and_kinds -q` | No - W0 | pending |
| 37-02-02 | 02 | 1 | PROV-02, PROV-05 | unit + CLI | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_collect_provider_audio_checks_is_non_destructive tests/test_call_ready_cli.py::test_call_ready_provider_audio_checks_are_non_destructive -q` | No - W0 | pending |
| 37-03-01 | 03 | 1 | PROV-03 | unit | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_provider_capabilities_are_reported_without_actions -q` | No - W0 | pending |
| 37-03-02 | 03 | 1 | PROV-04 | unit + remediation | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_permission_blockers_are_actionable tests/analysis/test_remediation.py::test_launch_provider_audio_hints_classify_permissions -q` | No - W0 | pending |
| 37-04-01 | 04 | 2 | PROV-01..PROV-05 | integration | `uv run pytest tests/analysis/test_provider_audio_readiness.py tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/test_hotkey_doctor.py tests/analysis/test_remediation.py -q` | Mixed | pending |
| 37-04-02 | 04 | 2 | PROV-05 | regression | `uv run pytest tests/analysis/test_provider_audio_readiness.py::test_collect_provider_audio_checks_is_non_destructive tests/test_call_ready_cli.py::test_call_ready_provider_audio_checks_are_non_destructive -q` | No - W0 | pending |

*Status: pending -> green/red/flaky is updated by execution summaries.*

---

## Wave 0 Requirements

- [ ] `tests/analysis/test_provider_audio_readiness.py` - stubs and failing tests for PROV-01 through PROV-05 helper behavior.
- [ ] `tests/test_call_ready_cli.py` - call-ready rows, artifact, and non-destructive assertions for PROV-01 and PROV-05.
- [ ] `tests/analysis/test_launch_readiness.py` - update Phase 36 placeholder-order coverage to expect Phase 37 real checks.
- [ ] `tests/analysis/test_remediation.py` - launch provider/audio category coverage for `audio-device`, `provider`, and `macos-permission`.

---

## Manual-Only Verifications

All Phase 37 readiness behavior has automated verification through mocked
providers and audio devices. Manual live Chrome/Glip permission checks may be
useful after implementation, but they are not required to mark the phase
complete because default `call-ready` must remain non-destructive and fully
mock-testable.

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 90s for focused checks
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-08
