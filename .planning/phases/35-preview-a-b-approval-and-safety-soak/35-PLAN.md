# Phase 35 Plan: Preview, A/B Approval, and Safety Soak

**Created:** 2026-07-07
**Status:** Ready for execution

## Goal

Prove that cloned voice output is previewed, approved, and covered by the same
pre-call safety gates before it reaches a real call.

## Requirements Covered

SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05

## Plan 35-01: Approval Evidence Contracts

**Files:**
- `saymo/analysis/voice_approval.py`
- `tests/analysis/test_voice_approval.py`

**Steps:**
1. Validate completed/scored benchmark reports.
2. Require similarity/artifact/call-readiness gates or explicit override.
3. Update profile approval state atomically without touching referenced WAV/TXT.

## Plan 35-02: Approval and Rejection CLI

**Files:**
- `saymo/commands/voice_clone.py`
- `tests/test_voice_clone_cli.py`

**Steps:**
1. Add `voice-profile approve --apply`.
2. Add `voice-profile reject --apply`.
3. Show approval state and linked evidence in `voice-profile show`.

## Plan 35-03: Preview Audit

**Files:**
- `saymo/analysis/voice_approval.py`
- `saymo/commands/voice_clone.py`
- `tests/analysis/test_voice_approval.py`
- `tests/test_voice_clone_cli.py`

**Steps:**
1. Add preview audit sidecar that stores selector metadata and text hash only.
2. Add `voice-preview --dry-run` for audit-only preview checks.
3. Keep real playback local/monitor-only.

## Plan 35-04: Safety Soak Voice Violations

**Files:**
- `saymo/analysis/safety_soak.py`
- `tests/analysis/test_safety_soak.py`

**Steps:**
1. Fail safety soak on voice selector/cache/profile blocker text.
2. Preserve existing handbrake and unapproved-draft rules.

## Verification Commands

```bash
uv run pytest tests/analysis/test_voice_approval.py tests/test_voice_clone_cli.py tests/analysis/test_safety_soak.py
uv run pytest -q
```
