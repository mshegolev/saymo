# Implementation Handoff

**Updated:** 2026-10-24

**Branch:** `feat/live-translate`

**State:** committed and pushed; not merged to `main` and not tagged as a release.

## Completed work

### Scheduled meeting preparation and speech review

- Added `saymo daily-prep` to prepare a profile's spoken update, open its meeting
  URL when configured, and show a Play/Stop window.
- Added per-profile `saymo daily-prep-agent` commands backed by a macOS
  LaunchAgent schedule.
- Play uses cached speech and records the configured local microphone; Stop
  saves the recording and starts offline transcription plus local Ollama speech
  coaching. The resulting report is stored under `~/.saymo/speech_reviews/`.
- Configuration and operator notes are in `config.example.yaml` and
  `docs/DAILY-PREP.md`.
- Commit: `30d9ff7 feat: add scheduled meeting prep workflow`.

### BMAD status source plugin

- Added the `bmad` source plugin, selectable via `speech.source: bmad` or
  `--source bmad`.
- Reads the configured BMAD project's sprint/workflow YAML and summarizes
  progress, active/blocked work, and planned stories. It is read-only.
- Configure `bmad.project_path` and the optional status-file paths in
  `config.yaml`; details are in `docs/BMAD-PLUGIN.md`.
- The plugin is discoverable with `saymo list-plugins`.
- Commit: `60f48d7 feat(plugins): add BMAD sprint status source`.

## Verification

- `uv run pytest`: **643 passed, 1 skipped**.
- `uv run saymo list-plugins`: lists `bmad`.
- `uv run saymo speak --help` and `uv run saymo prepare --help`: both show
  `bmad` as a source option.
- The skipped test is the existing MLX test; pytest reports that the installed
  MLX binary is arm64 while this Python process is x86_64.

## Follow-up for the next session

- Try `saymo prepare --source bmad --no-save` with a BMAD project whose story
  statuses are populated; verify the composed speech and adjust parsing if
  that project uses a different BMAD status-file layout.
- Test the LaunchAgent schedule and the speech-review flow manually on macOS.
- Local `logs/` artifacts were not committed; they remain in the working tree.
