# Contributing to Saymo

Thanks for your interest in Saymo. This document covers how to set up a dev environment, what conventions to follow, and how to submit changes.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating you agree to abide by its terms.

## Quick links

- 🐛 [Report a bug](.github/ISSUE_TEMPLATE/bug_report.yml)
- 💡 [Request a feature](.github/ISSUE_TEMPLATE/feature_request.yml)
- 🔒 [Security disclosures](SECURITY.md) (do not file as a public issue)
- 📚 [Architecture / design docs](docs/)
- 📓 [Changelog](CHANGELOG.md)

## Dev setup

```bash
git clone https://github.com/<org>/saymo.git
cd saymo
./install.sh           # uv-based venv at .venv/, models, Chrome JS
source .venv/bin/activate
saymo --help
```

Saymo requires:
- macOS on Apple Silicon (arm64)
- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- [BlackHole](https://github.com/ExistentialAudio/BlackHole) virtual audio (`brew install blackhole-2ch blackhole-16ch`)
- [Ollama](https://ollama.com) for local LLM inference

## Project layout

See `CLAUDE.md` for an annotated map. High-level:

```
saymo/
├── cli.py                 # Click entry-point
├── config.py              # YAML loader
├── audio/                 # Capture, playback, BlackHole routing
├── analysis/              # Trigger detection (name match)
├── speech/                # LLM composers (Ollama / Anthropic)
├── tts/                   # XTTS / Qwen3 / Piper / macOS say
├── plugins/               # Pluggable task sources (Jira, Notion, Obsidian)
└── providers/             # Per-call-app Chrome automation
```

## Conventions

These come from `CLAUDE.md`; new code should follow them.

- **No personal data in source.** Names, codenames, project-specific words go through `config.yaml`. Source stays generic.
- **Local by default.** Cloud providers (Anthropic, OpenAI, ElevenLabs, Deepgram) are optional and disabled in the example config. On-device paths must keep working without API keys.
- **Prompts live in `saymo/speech/ollama_composer.py`** as `DEFAULT_*_PROMPT_*` constants and are overridable via `config.prompts.<key>`. When changing a prompt, update both the default and `config.example.yaml` docs.
- **Vocabulary in `saymo/tts/text_normalizer.ABBREV_MAP`** is generic IT/DevOps only. Project-specific terms go in `config.vocabulary.abbreviations`.
- **Prefer dataclasses for typed config.** See `SaymoConfig` in `saymo/config.py`.
- **Logging.** `logger = logging.getLogger("saymo.<module>")`.
- **Tests** live in `tests/` and use `pytest`.

## Coding style

- Python 3.12+, type hints encouraged but pragmatic
- 4-space indent, no tabs
- `ruff` / `black` formatting (project doesn't pin a formatter; match surrounding style)
- Imports grouped: stdlib → third-party → first-party (`saymo.*`)

## Running tests

```bash
uv run pytest                    # all tests
uv run pytest tests/tts          # one folder
uv run pytest -k "factory"       # by name pattern
```

Add a test for any non-trivial bug fix or feature. Voice-quality changes should also include a manual A/B step in the PR description (e.g. "verified with `saymo train-eval`").

## Pull requests

1. Fork → branch off `main` → push to your fork.
2. Open a PR using the template (`.github/PULL_REQUEST_TEMPLATE.md`).
3. Describe **what** changed and **why**, link any issue.
4. Keep PRs focused — separate refactors from feature work where reasonable.
5. CI must pass (when CI is added). Local `uv run pytest` should be green.

### Commit messages

Conventional-ish prefix is appreciated but not enforced:
- `feat(tts):`, `fix(audio):`, `docs:`, `chore:`, `refactor:`, `test:`

Subject line ≤72 chars; body wraps at 72; reference issues with `Fixes #123`.

## Areas where help is welcome

- **Voice quality:** new TTS engines, RVC tuning, dataset cleaning utilities
- **Call providers:** add support for new video-call apps under `saymo/providers/`
- **Languages:** prompts and abbreviations are Russian-first; PRs that generalize are welcome
- **Tests:** any module without coverage is fair game

## Questions

For non-bug discussion, open a GitHub Discussion (preferred) or ping the maintainers in an issue.
