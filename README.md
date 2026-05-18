# Saymo — Local AI Voice Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](pyproject.toml)
[![Platform: macOS arm64](https://img.shields.io/badge/platform-macOS%20arm64-lightgrey.svg)](#requirements)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

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

## Quick install — one command

```bash
git clone https://github.com/acme/saymo && cd saymo
./setup.sh
```

`setup.sh` is the **master orchestrator** — it walks you through:
1. Saymo core (uv venv, Ollama, Whisper, BlackHole)
2. F5-TTS Russian voice cloning *(recommended)*
3. XTTS+RVC pipeline *(optional alternative)*
4. Interactive wizard for `~/.saymo/config.yaml`

Each step asks before doing anything heavy. Re-runnable; skips what's already installed. Total time on a fresh Mac: **~30 minutes** (most spent on model downloads).

For the full walkthrough see [`docs/QUICK-START.md`](docs/QUICK-START.md).

## First-time setup

After `setup.sh` finishes, run:

```bash
saymo test-tts "Привет, это тест"  # Check that TTS works
saymo test-devices                 # Verify audio devices
```

To re-configure later:
```bash
saymo setup                        # Interactive: name, devices, TTS engine
saymo record-voice -d 12           # Record a fresh ~12s voice reference
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
saymo prepare-responses         # pre-synthesize the Q&A library for live mode
saymo auto-preflight -p personal
saymo review                    # optional: check generated audio

# During the call
saymo speak -p personal         # manual trigger, instant playback
saymo auto -p personal          # listen for your name, speak when called
saymo auto -p personal --mic    # same, but from laptop mic (for testing)
saymo trigger-capture -p personal --window 8
                                # save call windows classified for trigger training

# Extras
saymo dashboard                 # interactive TUI
```

### Auto-mode hotkeys

```bash
./scripts/add_hotkeys.py
saymo takeover-check -p personal
```

Default hotkeys:

| Hotkey | Action |
|---|---|
| `Cmd+Shift+S` | Speak the prepared cached standup immediately in `saymo auto` |
| `Cmd+Shift+U` | Manual takeover: stop Saymo playback, pause auto-mode, switch the call mic to your real mic when the provider supports it; press again to return to BlackHole 2ch and resume |
| `Cmd+Shift+X` | Stop current Saymo playback |
| `Cmd+Shift+M` | Pause / resume auto-mode |

Mic switching is automatic for providers that implement `switch_mic()`
(`glip`, `mts_link`). For other providers, Saymo still pauses/resumes; switch
the call microphone manually in the meeting UI.
Use `saymo takeover-check -p personal` before a call to verify mic switching
against the active Chrome tab.

### Trigger training capture

Use `trigger-capture` when you want to collect real call phrases for improving
trigger detection:

```bash
saymo trigger-capture -p personal
saymo trigger-capture -p personal --device "MacBook Pro Microphone" --duration 60
saymo trigger-eval -p personal
```

By default it listens on `audio.capture_device`, normally `BlackHole 16ch`.
Each window is saved as WAV plus JSON metadata under
`~/.saymo/trigger_samples/<profile>/` and separated into:
`asked_to_speak`, `question`, and `speech`. Add `--save-silence` only when you
also need silent windows for debugging.

Review the saved windows without opening JSON by hand:

```bash
saymo trigger-samples list -p personal
saymo trigger-samples label ~/.saymo/trigger_samples/personal/question/<sample>.json --speaker other
saymo trigger-samples replay ~/.saymo/trigger_samples/personal/asked_to_speak/<sample>.json
saymo trigger-eval -p personal --promote ~/.saymo/trigger_samples/personal/asked_to_speak/<sample>.json
saymo trigger-samples report -p personal -o ~/.saymo/trigger_samples/personal-report.md
```

`trigger-eval` compares stored and current classification, reports misses and
false positives, groups results by speaker label (`me`, `other`, `unknown`),
and can promote a heard name variant into `vocabulary.fuzzy_expansions` before
re-running the evaluation. Use `trigger-samples label` to correct who spoke in a
saved window; old samples without a label are treated as `unknown`. Reports
omit raw audio and transcript text.

### Call providers

`saymo auto` works with all Chrome-based call apps — the provider is
picked by `meetings.<profile>.provider` in config:

| `provider:` | Service |
|---|---|
| `glip` (default) | RingCentral Glip |
| `zoom` | Zoom |
| `google_meet` | Google Meet |
| `ms_teams` | Microsoft Teams |
| `telegram` | Telegram calls (web) |
| `telemost` | Yandex Telemost |
| `vk_teams` | VK Teams |
| `mts_link` | MTS Link |

Run `saymo list-plugins` to see everything available in your install.

### Live Q&A mode

When your name is called and the surrounding transcript looks like a
question, `auto` consults a **pre-synthesised response library** and plays
the best-matching cached variant — no network hop, no synthesis lag.
Populate the library once with `saymo prepare-responses`. Built-in
intents cover status (`как дела`), blockers, ETA, testing stage, review.
Extend with your own wording via `config.responses.library`.

On cache miss, you can opt into a **live fallback**: Ollama composes an
answer from your standup summary + JIRA context, the TTS engine
synthesizes it, and Saymo plays it back. This adds a few seconds of
latency but covers any question. Enable it in config:

```yaml
responses:
  live_fallback: true
```

Without `live_fallback` (default), a cache miss falls back to the
generic standup audio — quiet, reliable, no LLM dependency.

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

To check whether a live phrase will trigger Saymo before joining a call:

```bash
saymo trigger-check -p personal --text "John, что по статусу?"
saymo trigger-check -p personal --mic
saymo auto-preflight -p personal
saymo trigger-setup -p personal --heard "Jon, что по статусу?"
saymo trigger-learn -p personal --heard "Jon"
```

The diagnostic shows trigger match, whether the mention is addressed to you,
question detection, confirmation behavior, auto-mode action, and response-cache
routing. `auto-preflight` checks prepared audio, devices, provider readiness,
profile triggers, response-cache coverage, fallback mode, and live tuning.
Use `trigger-setup` when Whisper consistently hears your name as a different
spelling; it updates `vocabulary.fuzzy_expansions` and verifies the learned
variant immediately. You can paste the whole transcribed phrase; Saymo extracts
the likely name variant before saving it.
When `safety.require_confirmation` is enabled, auto-mode waits for a second
trigger mention within `safety.confirmation_timeout_seconds` before speaking;
this helps suppress accidental mentions in live calls.

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

## Voice cloning quality tiers

Multiple paths for getting your own voice on calls — pick the one that matches your patience and quality bar:

| Tier | Setup | Time | Subjective similarity | Doc |
|---|---|---|---|---|
| Zero-shot XTTS | `saymo record-voice` | 5 min | ~5/10 | — |
| Fine-tuned XTTS | + `saymo train-voice` | 2-3 h | ~7-8/10 | [`docs/VOICE-TRAINING.md`](docs/VOICE-TRAINING.md) |
| Fine-tuned XTTS + RVC | + `scripts/install_rvc.sh` | +1-2 h | 9-10/10 | [`docs/RVC-VOICE-CLONING.md`](docs/RVC-VOICE-CLONING.md) |
| **F5-TTS Russian (alt path)** | `scripts/install_f5tts.sh` | ~10 min | 9-10/10 | [`docs/F5TTS-VOICE-CLONING.md`](docs/F5TTS-VOICE-CLONING.md) |

If your voice "sounds close but not quite you" after XTTS fine-tune, that's the XTTS speaker-encoder ceiling. RVC swaps the timbre on top to break through. **F5-TTS** is a one-stage alternative — Russian-purpose-built model, no second pass, simpler pipeline.

## Security & privacy

- Everything runs on-device by default. Cloud TTS / STT providers are optional and disabled in the example config.
- Voice samples and secrets are listed in `.gitignore` — they never leave your machine.
- Prompts, vocabulary, trigger phrases are all in your config file — source stays generic.

## Project resources

- [`docs/QUICK-START.md`](docs/QUICK-START.md) — **start here** if you're new
- [`docs/OVERVIEW.md`](docs/OVERVIEW.md) — what Saymo is, how it's wired
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup, conventions, PR workflow
- [`CHANGELOG.md`](CHANGELOG.md) — version history (Keep a Changelog)
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Contributor Covenant 2.1
- [`SECURITY.md`](SECURITY.md) — vulnerability reporting + threat model
- [`docs/`](docs/) — voice training, RVC, F5-TTS, ADRs, PRDs

Bug? Idea? Use the issue templates under [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/).

## License

MIT — see [`LICENSE`](LICENSE).

## Acknowledgements

- [Coqui TTS](https://github.com/coqui-ai/TTS) for XTTS v2.
- [Ollama](https://ollama.com) for local LLM hosting.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for transcription.
- [BlackHole](https://existential.audio/blackhole/) for virtual audio routing.
