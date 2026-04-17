# Saymo — Local AI Voice Assistant

Fully local AI voice assistant for macOS. Speaks into any live call in **your cloned voice** — no cloud APIs required.

Saymo composes short, natural speech from optional data sources (tracker, notes, text files), synthesizes it with voice cloning, and routes audio into the active call through a virtual microphone. Everything — language model, speech-to-text, text-to-speech — runs on-device.

- **Local:** Ollama + faster-whisper + Coqui XTTS v2 (or Piper / macOS `say` as fallback).
- **Voice cloning:** 5-minute sample → your voice, fine-tuning optional.
- **Routing:** BlackHole virtual mic → any browser-based call app.
- **Call automation:** Chrome-driven mute/unmute for 8 providers (Glip, Zoom, Google Meet, MS Teams, Telegram, Yandex Telemost, VK Teams, MTS Link).
- **Listening mode:** auto-detects when your name is called, answers questions from provided context.
- **User-configurable prompts and vocabulary** — no source edits required.

> **Project status:** early public alpha. Expect rough edges. Contributions welcome.

---

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4), **arm64 terminal, not Rosetta**
- Python 3.11+
- Homebrew
- Google Chrome
- ~10 GB free disk space

## Quick install

```bash
git clone https://github.com/mshegolev/saymo && cd saymo
cp config.example.yaml config.yaml   # fill in your details
./install.sh
```

The installer handles brew deps, Python packages (via `uv` or `pip`), an Ollama check, a Piper voice model, and Chrome permissions.

## First-time setup

```bash
saymo setup                        # Interactive wizard: name, devices, profiles
saymo record-voice -d 300          # Record a 5-minute voice sample
saymo test-devices                 # Verify audio devices
saymo test-tts "Привет, это тест"  # Check that TTS works
```

### One-time audio routing

```
┌─────────────────────────────────────────────────────────────┐
│                   Audio MIDI Setup                          │
│  Create "Multi-Output Device":                              │
│    ✓ Your headphones   (master, no drift correction)        │
│    ✓ BlackHole 16ch    (drift correction ON)                │
│                                                             │
│  In your call app:                                          │
│    Microphone → BlackHole 2ch                               │
│    Speakers   → Multi-Output Device                         │
└─────────────────────────────────────────────────────────────┘
```

## Daily usage

```bash
# Before the call: prepare text + cached audio
saymo prepare -p personal
saymo review                    # optional: check generated audio

# During the call
saymo speak --glip              # manual trigger, instant playback
saymo auto -p personal          # listen for your name, speak when called

# Extras
saymo dashboard                 # interactive TUI
```

## Configurable prompts

All LLM prompts are templates loaded from `config.yaml` → `prompts.*` at runtime, with sensible generic defaults in source. To customize voice/tone:

```yaml
prompts:
  standup_ru: |
    Ты — помощник для ежедневных встреч. Составь отчёт на русском...
    {yesterday_notes}
    {today_notes}
  qa_system_ru: |
    Ты — {user_name}, {user_role}. Отвечай кратко, 1-3 предложения...
```

See `config.example.yaml` for all available keys and the default set.

## Project-specific vocabulary

Adding your own abbreviations or fuzzy name expansions to the TTS normalizer is done through config, not source:

```yaml
vocabulary:
  abbreviations:
    MYAPI: "май-эй-пи-ай"
    K8S: "кубернетес"
  fuzzy_expansions:
    Alex: ["Alex", "Алекс", "Саша", "Саня"]
```

## Architecture

```
┌───────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────────┐
│ Source plugin │──▶│ LLM composer │──▶│ Text normalizer│──▶│  TTS engine  │
│  (optional)   │   │   (Ollama)   │   │   (abbrevs,    │   │  (XTTS clone │
│               │   │              │   │    numbers)    │   │  / Piper)    │
└───────────────┘   └──────────────┘   └────────────────┘   └──────┬───────┘
                                                                   │
┌──────────────┐   ┌──────────────┐   ┌────────────────┐           │
│Call provider │◀──│ Auto trigger │◀──│  STT (Whisper) │       Audio bytes
│(mute/unmute) │   │(name detect) │   │ (capture call) │           │
└──────┬───────┘   └──────────────┘   └────────────────┘           │
       │                                                           │
       ▼                                                           ▼
  BlackHole 2ch ─────────────────────────────────────────── Audio output + monitor
  (virtual mic)
```

Details in `docs/PRD.md` and ADRs under `docs/adr/`.

## Security & privacy

- Everything runs on-device by default. Cloud TTS / STT providers are optional and disabled in the example config.
- Voice samples and secrets are listed in `.gitignore` — they never leave your machine.
- Prompts, vocabulary, trigger phrases are all in your config file — source stays generic.

## License

MIT — see [`LICENSE`](LICENSE).

## Acknowledgements

- [Coqui TTS](https://github.com/coqui-ai/TTS) for XTTS v2.
- [Ollama](https://ollama.com) for local LLM hosting.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for transcription.
- [BlackHole](https://existential.audio/blackhole/) for virtual audio routing.
