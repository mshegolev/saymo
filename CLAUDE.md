# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Saymo

Saymo is a fully local AI-powered standup automation tool for Glip calls. It fetches JIRA tasks, composes a natural standup summary via a local LLM, and speaks it using voice cloning — all without cloud APIs.

## Install

```bash
./install.sh   # installs all deps, checks audio devices, enables Chrome JS
```

## Pipeline

```
JIRA tasks (confluence JQL) → Ollama (qwen2.5-coder:7b) → Text Normalizer → XTTS v2 (cloned voice) → Audio Device
```

Three task sources: `confluence` (default, same JQL as update_confluence.py), `obsidian` (daily notes), `jira` (simple query).
Three TTS engines: `coqui_clone` (XTTS v2 voice clone), `piper` (fast neural), `macos_say` (builtin fallback).

## Commands

```bash
# Setup
./install.sh                             # Full installation
python3 -m saymo record-voice -d 300     # Record 5-min voice sample
python3 -m saymo test-devices            # List audio devices

# Daily standup (personal)
python3 -m saymo prepare                 # JIRA → Ollama → TTS → cache audio
python3 -m saymo review                  # Listen sentence-by-sentence, fix quality
python3 -m saymo speak --glip            # Instant playback into Glip call

# Team scrum (Михаил + Олег)
python3 -m saymo prepare --team          # Fetch both members' tasks
python3 -m saymo speak --team --glip     # Play team report

# Auto mode (name trigger)
python3 -m saymo auto                    # Listen for "Михаил/Миша", auto-speak
python3 -m saymo auto --mic              # Test with own microphone

# Interactive
python3 -m saymo dashboard              # TUI with hotkeys (p/s/g/d/e/t/x/q)

# Testing
python3 -m saymo test-tts "text"         # Test TTS engine
python3 -m saymo test-ollama             # Check Ollama status
python3 -m saymo test-jira               # Test JIRA connection
python3 -m saymo test-notes              # Show Obsidian daily notes
python3 -m saymo test-compose            # Generate text without audio
```

## Architecture

- `saymo/cli.py` — Click CLI. Core flow: `_get_standup_content()` → `_compose_text()` → `_speak_text()`. Three-level cache: audio → text → full pipeline.
- `saymo/tui.py` — Interactive dashboard with Rich Live, background async tasks via threading.
- `saymo/glip_control.py` — Chrome automation via AppleScript + JS injection. Find Glip tab, switch mic, unmute/speak/mute.
- `saymo/jira_source/confluence_tasks.py` — Personal and team task fetch. Same JQL as update_confluence.py.
- `saymo/speech/ollama_composer.py` — Standup text via Ollama. Personal prompt (first person) + team prompt (I + Олег).
- `saymo/tts/coqui_clone.py` — XTTS v2 voice cloning. Voice sample at `~/.saymo/voice_samples/voice_sample.wav`.
- `saymo/tts/text_normalizer.py` — Expands abbreviations, strips build versions, IT terms → Russian phonetics.
- `saymo/audio/capture.py` — Overlapping sliding window capture (4s chunks, 2s overlap) for auto mode.
- `saymo/stt/whisper_local.py` — faster-whisper (local STT, no API).
- `saymo/analysis/turn_detector.py` — Fuzzy name detection with cooldown.
- `saymo/config.py` — Dataclass config with `${ENV_VAR}` substitution.

## Key Dependencies

- **PyTorch 2.11+ (arm64)** — must run in native arm64 terminal, NOT Rosetta
- **coqui-tts** — `pip install coqui-tts[codec]`
- **Ollama** — `ollama serve`, model: `qwen2.5-coder:7b`
- **FFmpeg** — `brew install ffmpeg`
- **BlackHole** — `brew install blackhole-2ch blackhole-16ch`
- **selfhelper** at `/opt/develop/selfhelper` — JIRA credentials

## Audio Routing

```
Saymo TTS → BlackHole 2ch → Glip mic input (others hear)
          → Plantronics   → Headphones (you hear yourself)

Glip speakers → Multi-Output Device → Plantronics (you hear others)
                                    → BlackHole 16ch (Saymo listens for auto mode)
```

## Adding Abbreviations

Edit `ABBREV_MAP` in `saymo/tts/text_normalizer.py`:
```python
"NEW_ABBR": "произношение",
```

## Adding Team Members

Edit `TEAM_MEMBERS` in `saymo/jira_source/confluence_tasks.py`:
```python
"username": "Display Name",
```
