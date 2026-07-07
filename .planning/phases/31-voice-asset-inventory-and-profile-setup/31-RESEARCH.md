# Phase 31 Research: Voice Asset Inventory and Profile Setup

**Researched:** 2026-07-07
**Status:** Ready for planning

## Implementation Facts

- Commands are registered by importing submodules in `saymo/commands/__init__.py`.
  A new `saymo/commands/voice_clone.py` module should use `@main.command(...)`
  or `@main.group(...)` and then be imported in the registration line.
- Existing config is dataclass based in `saymo/config.py`; `load_config`
  resolves YAML into nested dataclasses. This phase can avoid config schema
  churn by accepting profile directories as conventional paths and by reading
  existing `config.tts` fields.
- Known engine keys are already centralized in `saymo/tts/factory.py` as
  `KNOWN_ENGINES` and `is_known_engine`.
- F5 runtime defaults are in `saymo/tts/f5tts.py`: reference sample defaults to
  `~/.saymo/voice_samples/voice_sample.wav`, F5 venv defaults to
  `~/F5TTS/.venv/bin/python`, and transcript sidecar is `<voice_sample>.txt`.
- Existing CLI tests use `click.testing.CliRunner`, temp YAML config files, and
  monkeypatch/temp paths. Phase 31 tests should follow that style and must not
  require real local models.

## Proposed Modules

- `saymo/analysis/voice_inventory.py`
  - Dataclasses: `VoiceAssetRecord`, `VoiceInventoryReport`.
  - Core function: `build_voice_inventory(config, saymo_home=None, f5_root=None)`.
  - Output helpers: `voice_inventory_to_json`, `render_voice_inventory_markdown`.
  - Read-only behavior: only `exists`, `stat`, optional SHA for small files,
    optional audio metadata through `soundfile`.
- `saymo/analysis/voice_profile.py`
  - Dataclasses: `VoiceProfileManifest`, `VoiceProfileCheck`.
  - Core functions: `build_voice_profile_manifest`, `write_voice_profile_manifest`,
    `load_voice_profile_manifest`, `check_voice_profile`.
  - Storage: `~/.saymo/voice_profiles/<profile>/profile.json`.
  - Approval starts false; approvals are Phase 35.
- `saymo/commands/voice_clone.py`
  - Commands: `voice-inventory`, `voice-profile init`, `voice-profile show`,
    `voice-profile check`.

## Test Strategy

- `tests/analysis/test_voice_inventory.py`
  - Inventory classifies voice sample, transcript, training dataset, F5 paths,
    benchmark root, audio cache, and known engine state.
  - Inventory export is sanitized and omits transcript text.
  - Inventory does not mutate source file contents or mtimes.
- `tests/analysis/test_voice_profile.py`
  - Profile manifest references existing WAV/TXT and stores hashes/metadata.
  - Dry-run manifest creation does not write.
  - Explicit write is atomic enough for normal local use and preserves source
    files.
  - Profile check detects missing reference and stale hash.
- `tests/test_voice_clone_cli.py`
  - `saymo voice-inventory --json-output` writes JSON report.
  - `saymo voice-profile init --dry-run` prints proposed profile but does not
    write.
  - `saymo voice-profile init --apply` writes the manifest.
  - `saymo voice-profile show/check` report status from the written manifest.

## Risks

- Broad home directory scans would be slow. Inventory must inspect only known
  configured/conventional paths.
- Transcript text can leak. Store/report transcript path and character count,
  not content.
- Large models should not be hashed recursively. Hash only reference files and
  small files; classify large directories by path/size.
- This phase should not add runtime selector behavior; that is Phase 34.

