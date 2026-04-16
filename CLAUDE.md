# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Saymo

Saymo is a fully local AI-powered standup automation tool for Glip (RingCentral) calls. It fetches JIRA tasks, composes a natural standup summary via a local LLM, and speaks it using voice cloning — all without cloud APIs.

## Pipeline

```
JIRA tasks (confluence JQL) → Ollama (qwen2.5-coder:7b) → Text Normalizer → XTTS v2 (cloned voice) → Audio Device
```

Three task sources: `confluence` (default, same JQL as update_confluence.py), `obsidian` (daily notes), `jira` (simple query).
Three TTS engines: `coqui_clone` (XTTS v2 voice clone), `piper` (fast neural), `macos_say` (builtin fallback).

## Commands

```bash
python3 -m saymo dashboard          # Interactive TUI — switch devices/engines, prepare & speak
python3 -m saymo prepare             # Fetch JIRA → compose summary → save to Obsidian
python3 -m saymo speak               # Voice the summary to configured audio device
python3 -m saymo speak --source obsidian --composer ollama
python3 -m saymo test-devices        # List audio devices
python3 -m saymo test-tts "text"     # Test TTS engine
python3 -m saymo test-ollama         # Check Ollama status
python3 -m saymo record-voice -d 30  # Record voice sample for cloning
```

## Architecture

- `saymo/cli.py` — Click CLI, all commands. `_get_standup_content()` → `_compose_text()` → `_speak_text()` is the core flow.
- `saymo/tui.py` — Interactive dashboard with Rich Live display, background async tasks via threading.
- `saymo/jira_source/confluence_tasks.py` — Fetches tasks using same JQL as `/Users/m.v.shchegolev/Downloads/qaa2/update_confluence.py`. Reuses selfhelper JIRA credentials.
- `saymo/speech/ollama_composer.py` — Composes standup text via local Ollama HTTP API (`/api/generate`).
- `saymo/tts/coqui_clone.py` — XTTS v2 voice cloning. Lazy-loads model (~2GB). Voice sample at `~/.saymo/voice_samples/voice_sample.wav`.
- `saymo/tts/text_normalizer.py` — Expands abbreviations (NS2→эн-эс-два), numbers, versions before TTS. `ABBREV_MAP` dict is the source of truth.
- `saymo/tts/piper_tts.py` — Fast local TTS via Piper CLI. Model at `~/.saymo/piper_models/`.
- `saymo/obsidian/daily_notes.py` — Reads Obsidian vault daily notes by date pattern.
- `saymo/config.py` — Dataclass-based config with `${ENV_VAR}` substitution. Loaded from `config.yaml`.

## Key Dependencies

- **PyTorch 2.11+ (arm64)** — required for XTTS v2. Must run in native arm64 terminal, NOT Rosetta.
- **coqui-tts** — XTTS v2 voice cloning. Install with `pip install coqui-tts[codec]`.
- **Ollama** — local LLM. Must be running (`ollama serve`). Model: `qwen2.5-coder:7b`.
- **FFmpeg** — required by torchcodec for audio loading. `brew install ffmpeg`.
- **BlackHole** — virtual audio for Glip routing. `brew install blackhole-2ch`.
- **selfhelper** at `/opt/develop/selfhelper` — provides JIRA credentials via `config.constants`.

## Config

`config.yaml` in project root. Key settings:
- `speech.source`: `confluence` | `obsidian` | `jira`
- `speech.composer`: `ollama` | `anthropic`
- `tts.engine`: `coqui_clone` | `piper` | `macos_say` | `openai`
- `audio.playback_device`: device name (e.g., `Plantronics Blackwire 3220 Series`, `BlackHole 2ch`)
- `user.name_variants`: trigger phrases for turn detection (Phase 3)

## Audio Routing for Glip

BlackHole 2ch acts as virtual microphone:
1. Glip → Microphone → `BlackHole 2ch`
2. Saymo → playback_device → `BlackHole 2ch`
3. Glip hears Saymo's output as mic input

## Adding Abbreviations

Edit `ABBREV_MAP` in `saymo/tts/text_normalizer.py`:
```python
"NEW_ABBR": "произношение",
```
