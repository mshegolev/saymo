# Repository Guidelines

Saymo is a fully local AI voice assistant for macOS that speaks in a user's cloned voice on live calls. This guide is for contributors and AI coding agents working in this repo. For deeper architectural notes, see `CLAUDE.md` and `docs/`.

## Project Structure & Module Organization

- `saymo/` — main Python package
  - `cli.py` — Click entry-point (`saymo` command)
  - `config.py`, `wizard.py` — YAML config + interactive setup
  - `audio/` — capture, playback, BlackHole routing
  - `analysis/` — turn detection (name → trigger)
  - `speech/` — LLM composers (`ollama_composer.py`, `composer.py`)
  - `tts/` — XTTS, Qwen3-TTS (MLX), Piper, macOS `say`, trainers, normalizers
  - `plugins/` — task sources (Jira, Notion, Obsidian)
  - `providers/` — per-call-app Chrome automation JS
- `tests/` — pytest suite, mirrors package layout (`tests/tts/`, `tests/audio/`, ...)
- `scripts/` — install/training shell helpers (e.g. `install_rvc.sh`, `train_rvc.sh`)
- `docs/` — design and how-to docs; `config.example.yaml` is the public template.

## Build, Test, and Development Commands

```bash
./install.sh                     # full setup: brew deps, uv venv, models, Chrome JS
source .venv/bin/activate        # activate dev env
saymo setup                      # interactive config wizard
saymo --help                     # list CLI commands
uv run pytest                    # run all tests
uv run pytest tests/tts          # run one folder
uv run pytest -k "factory"       # run by name pattern
uv sync                          # resync deps from uv.lock / pyproject.toml
```

## Coding Style & Naming Conventions

- Python 3.11+ (3.12 preferred), 4-space indent, no tabs (see `.editorconfig`).
- Type hints encouraged; prefer dataclasses for typed config (see `SaymoConfig`).
- Imports grouped: stdlib → third-party → first-party (`saymo.*`).
- Modules and functions: `snake_case`; classes: `PascalCase`; constants: `UPPER_SNAKE`.
- Logging: `logger = logging.getLogger("saymo.<module>")`.
- No formatter is pinned; match surrounding style. `ruff`/`black` welcome locally.
- Architectural rules: no personal data or codenames in source — route through `config.yaml`. Prompts live as `DEFAULT_*_PROMPT_*` in `saymo/speech/ollama_composer.py` and are overridable via `config.prompts.<key>`. Local-by-default: cloud providers must remain optional.
- TTS naturalness rules: when writing any new TTS-generation code or tweaking synthesis params, follow `docs/VOICE-NATURALNESS.md` and import presets/helpers from `saymo/tts/naturalness.py` (`NATURAL_PRESET`, `load_breath_sample`, `resolve_voice_sample`, `split_for_tts`). Don't redefine `speed`/`temperature`/`repetition_penalty` per-script — tune them in `naturalness.py` and the doc.

## Testing Guidelines

- Framework: `pytest` (see `[dependency-groups].dev` in `pyproject.toml`).
- Place tests under `tests/<area>/` mirroring the package; name files `test_*.py`.
- Add a test for any non-trivial bug fix or feature. For voice-quality changes, include a manual A/B note in the PR (e.g. `saymo train-eval`).
- Run `uv run pytest` before pushing; keep it green.

## Commit & Pull Request Guidelines

- Commit prefix style observed in history: `feat(tts):`, `fix(audio):`, `docs:`, `chore(deps):`, `refactor:`, `test:`. Subject ≤72 chars; reference issues with `Fixes #123`.
- Branch off `main`; keep PRs focused (separate refactors from features).
- PR description: what changed and why, linked issue, manual-test notes for audio/voice paths. Use `.github/PULL_REQUEST_TEMPLATE.md`.

## Security & Configuration Tips

- Secrets use `${ENV_VAR}` interpolation in `config.yaml`; never commit real keys.
- `config.yaml` is gitignored; update `config.example.yaml` when introducing new keys.
- Report vulnerabilities per `SECURITY.md` — do not open public issues.
