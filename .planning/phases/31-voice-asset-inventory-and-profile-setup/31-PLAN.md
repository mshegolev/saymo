# Phase 31 Plan: Voice Asset Inventory and Profile Setup

**Created:** 2026-07-07
**Status:** Ready for execution

## Goal

Deliver read-only voice asset inventory and protected voice profile/reference
setup without touching models, datasets, training, downloads, or runtime voice
selection.

## Requirements Covered

INV-01, INV-02, INV-03, INV-04, PROF-01, PROF-02, PROF-03, PROF-04

## Plan 31-01: Voice Inventory Contracts and Scanner

**Files:**
- `saymo/analysis/voice_inventory.py`
- `tests/analysis/test_voice_inventory.py`

**Steps:**
1. Write failing tests for inventory classification and transcript redaction.
2. Add dataclasses for asset records and report.
3. Implement targeted scanning for configured/conventional paths only.
4. Add JSON/Markdown serialization helpers.
5. Verify focused tests.

**Acceptance:**
- Inventory reports engines, voice samples, transcript sidecars, training
  datasets, F5 paths, benchmark root, and cache root.
- Protected assets are classified without mutation.
- Transcript text is not emitted in JSON/Markdown.

## Plan 31-02: Voice Profile Manifest and Checks

**Files:**
- `saymo/analysis/voice_profile.py`
- `tests/analysis/test_voice_profile.py`

**Steps:**
1. Write failing tests for manifest creation, no-write dry-run behavior, atomic
   write, and stale/missing reference checks.
2. Add dataclasses for profile manifest and check result.
3. Implement manifest builder using existing reference WAV/TXT metadata.
4. Implement load/write/check helpers.
5. Verify focused tests.

**Acceptance:**
- Profile manifests reference, not copy, WAV/TXT files.
- Approval starts false.
- Source files are not modified.
- Checks detect missing references and hash drift.

## Plan 31-03: CLI Commands

**Files:**
- `saymo/commands/voice_clone.py`
- `saymo/commands/__init__.py`
- `tests/test_voice_clone_cli.py`

**Steps:**
1. Write failing CLI tests for `voice-inventory`, `voice-profile init/show/check`.
2. Add a new command module and register it.
3. Wire commands to analysis modules with clear Rich output and JSON output.
4. Keep `--dry-run` and `--apply` explicit for profile writes.
5. Verify CLI tests.

**Acceptance:**
- CLI can run against temp config/assets.
- Dry-run prints but does not write profile files.
- Apply writes `profile.json`.
- Show/check read the manifest and report status.

## Plan 31-04: Docs and Verification

**Files:**
- `docs/voice-clone-shootout.md`
- `config.example.yaml`
- `.planning/STATE.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`

**Steps:**
1. Document inventory/profile workflow and protected-asset rule.
2. Add config comments only if new config keys are introduced.
3. Run focused tests, then full `uv run pytest` if feasible.
4. Update GSD requirement traceability for Phase 31.
5. Commit Phase 31 implementation.

**Acceptance:**
- Docs state no delete/download/training in inventory/profile commands.
- Focused tests pass.
- Phase 31 requirements can be marked complete after verification.

## Verification Commands

```bash
uv run pytest tests/analysis/test_voice_inventory.py tests/analysis/test_voice_profile.py tests/test_voice_clone_cli.py
uv run pytest
```

