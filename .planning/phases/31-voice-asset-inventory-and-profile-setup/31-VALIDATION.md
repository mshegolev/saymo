# Phase 31 Validation Strategy

**Created:** 2026-07-07

## Must Prove

- Inventory is read-only and does not mutate protected assets.
- Profile setup references existing assets and writes only explicit manifest
  metadata.
- CLI dry-run does not write.
- Sanitized output does not include transcript text.
- No tests require real local model paths, Qwen packages, network, or
  `~/.saymo`.

## Automated Coverage

- Unit tests for inventory classification/redaction/no-mutation.
- Unit tests for profile manifest/check helpers.
- CLI tests for inventory/profile commands.

## Manual Coverage

- Optional after implementation: run `saymo voice-inventory` locally and inspect
  that it lists real F5/Saymo assets without changing them.

