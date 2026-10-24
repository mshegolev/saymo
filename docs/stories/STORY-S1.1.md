# Verify the setup wizard end-to-end

- **ID:** S1.1
- **Epic:** Core Integration
- **Priority:** Must Have
- **Story Points:** 3
- **Status:** Completed

## User Story

As a new Saymo user, I want to complete the setup wizard and save a valid
configuration so that I can start using the CLI without editing YAML manually.

## Acceptance Criteria

- [x] The `saymo setup` command reaches all six wizard steps and exits cleanly
      when the user skips optional recording and meeting-profile setup.
- [x] The wizard writes a valid YAML configuration to the path supplied by the
      global `--config` option.
- [x] The saved configuration can be loaded through `load_config` and preserves
      the selected user, audio, Ollama, and TTS settings.
- [x] The verification runs without real audio hardware, voice recordings,
      Ollama services, or writes to the user's home configuration.

## Technical Notes

### Implementation Approach

Pass the root CLI's resolved config path into `run_wizard`. Exercise the actual
Click command with isolated device and Ollama adapters, then reload the emitted
YAML through the production config loader.

### Files/Modules Affected

- `saymo/commands/__init__.py` — forward the global config path to the wizard.
- `tests/test_wizard.py` — end-to-end command and config persistence test.
- `docs/stories/STORY-S1.1.md` — story scope and acceptance evidence.

### Edge Cases

- No audio input devices are available; the wizard still prompts for a device
  name and completes without opening an audio stream.
- No voice sample exists; the user declines recording.
- Meeting profile setup is skipped.
- Ollama is reported available by a test adapter, avoiding process startup or
  network calls during automated verification.

## Testing Requirements

### Unit and Integration Tests

- [x] Run the full six-step setup command with isolated adapters.
- [x] Parse the generated YAML and load it through `load_config`.
- [x] Confirm all six step headings are present and the command exits cleanly.

## Definition of Done

- [x] All acceptance criteria are verified by automated tests.
- [x] The focused and full test suites pass.
- [x] BMAD workflow status records the completed story.
