# CLAUDE.md

Guidance for Claude Code / other coding agents working in this repo.

## What Saymo is

Saymo is a **fully local AI voice assistant** for macOS. It composes short natural speech (via local Ollama), synthesizes it in the user's cloned voice (XTTS v2 / Piper / macOS `say`), and routes audio into any live call through a virtual microphone (BlackHole).

It supports 8 call providers over Chrome automation: Glip, Zoom, Google Meet, MS Teams, Telegram, Yandex Telemost, VK Teams, MTS Link. A built-in listening mode can detect when the user's name is called and answer questions from provided context.

## Install / run

```bash
./install.sh                       # Full setup (brew, uv/pip, models, Chrome JS)
saymo setup                        # Interactive wizard
saymo record-voice -d 300          # Record 5-minute voice sample
```

## Commands

```bash
# Before the call — prepare text + cached audio
saymo prepare -p <profile>
saymo review                       # review generated audio sentence-by-sentence

# During the call
saymo speak --glip                 # instant playback
saymo speak -p <profile> --glip
saymo auto -p <profile>            # listen → detect name → speak
saymo auto -p <profile> --mic      # test trigger via microphone

# Voice training (fine-tune for maximum similarity)
saymo train-prepare                # record 100 prompts with guided session
saymo train-voice --epochs 5       # fine-tune XTTS v2 GPT decoder (~2-3h)
saymo train-eval                   # A/B blind comparison (base vs fine-tuned)
saymo train-status                 # dataset & model status

# Misc
saymo dashboard                    # interactive TUI
saymo test-devices                 # list audio devices
saymo test-tts "<text>"            # test TTS engine
```

## Project layout

```
saymo/
├── cli.py                 # CLI entrypoint (Click)
├── config.py              # YAML loader (env-var resolution)
├── wizard.py              # Interactive setup
├── audio/                 # Capture, playback, devices, BlackHole routing
├── analysis/              # Turn detection (name → trigger)
├── speech/
│   ├── composer.py        # Cloud composer (optional, via Anthropic)
│   └── ollama_composer.py # Local LLM composer (DEFAULT prompts + overrides)
├── tts/
│   ├── qwen3_tts.py       # Qwen3-TTS voice cloning via MLX (recommended)
│   ├── qwen3_trainer.py   # Qwen3-TTS LoRA fine-tuning pipeline
│   ├── coqui_clone.py     # XTTS v2 voice cloning (legacy fallback)
│   ├── trainer.py         # XTTS v2 GPT decoder fine-tuning
│   ├── dataset.py         # Training dataset builder
│   ├── prompts.py         # Training prompts for recording
│   ├── quality.py         # A/B quality evaluation
│   └── text_normalizer.py # Abbreviations / numbers / tracker IDs stripping
├── plugins/               # Pluggable task sources (tracker, notes, files)
├── providers/             # Per-app Chrome automation (mute/unmute)
└── glip_control.py        # Chrome automation helper
```

## Architectural rules

- **Prompts are not hardcoded.** All user-facing LLM prompts live as `DEFAULT_*_PROMPT_*` constants in `saymo/speech/ollama_composer.py` (and `composer.py`) and are overridable via `config.prompts.<key>`. When touching a prompt, update both the default and the `config.example.yaml` docs.
- **Vocabulary is not hardcoded.** `saymo/tts/text_normalizer.ABBREV_MAP` covers only generic IT/DevOps terms. Project-specific names go in `config.vocabulary.abbreviations` and are merged at runtime. Do not add private/project codenames to source.
- **No personal data in source.** Usernames, team members, product codenames — all go through config. Source stays project-agnostic.
- **Local by default.** Cloud providers (Anthropic, OpenAI, ElevenLabs, Deepgram) are optional and disabled in the example config. Keep on-device paths working even when API keys are absent.
- **Fully local dependency chain:**
  - LLM → Ollama
  - STT → faster-whisper
  - TTS → Qwen3-TTS (MLX) / Coqui XTTS v2 / Piper / macOS `say`
  - Call automation → Chrome via per-provider JS in `saymo/providers/`.

## Audio routing

- Virtual mic: **BlackHole 2ch** (send Saymo output to the call app's microphone).
- Monitor: **Multi-Output Device** (your headphones + BlackHole 16ch) so you can hear what Saymo says alongside the call.
- Capture for auto-mode: read call audio via BlackHole 16ch → faster-whisper.

## Trigger detection

`TurnDetector` in `saymo/analysis/turn_detector.py` looks for name matches inside a sliding window (current chunk + previous). Name variants come from `config.user.name_variants`; optional fuzzy expansions for STT errors come from `config.vocabulary.fuzzy_expansions`. No names are hardcoded.

## Conventions

- Source of truth for configuration is `config.yaml` (user-local, gitignored). `config.example.yaml` is the public template.
- Secrets use `${ENV_VAR}` interpolation — values never land in git.
- Prefer dataclasses for typed config. See `SaymoConfig` in `saymo/config.py`.
- Log via `logger = logging.getLogger("saymo.<module>")`.
- Tests live in `tests/` (pytest).
