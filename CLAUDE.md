# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Saymo

Saymo is a fully local AI-powered standup automation tool. It fetches JIRA tasks, composes a natural standup summary via a local LLM (Ollama), and speaks it using voice cloning (XTTS v2) — all without cloud APIs. Supports 8 call providers via Chrome: Glip, Zoom, Google Meet, MS Teams, Telegram, Yandex Telemost, VK Teams, MTS Link.

## Install

```bash
./install.sh                         # Full setup (brew, uv/pip, models, Chrome JS)
saymo setup                          # Interactive wizard (name, devices, meetings)
saymo record-voice -d 300            # Record 5-min voice sample
```

## Commands

```bash
# Before meeting (prepare text + audio):
saymo prepare -p standup             # Personal standup
saymo prepare -p scrum               # Team scrum (Михаил + Олег)
saymo review                         # Review audio quality sentence-by-sentence

# During meeting:
saymo speak --glip                   # Instant playback (uses cached audio)
saymo speak -p scrum --glip          # Team report
saymo auto -p standup                # Full auto: listen → detect name → speak
saymo auto -p standup --mic          # Test trigger with own microphone

# Other:
saymo dashboard                      # Interactive TUI (p/s/g/d/e/t/x/q)
saymo test-devices                   # List audio devices
saymo test-tts "text"                # Test TTS engine
saymo test-ollama                    # Check Ollama status
```

## Pipeline

```
JIRA (confluence JQL) → Ollama (qwen2.5-coder:7b) → Text Normalizer → XTTS v2 (cloned voice) → Audio Device
```

Three-level cache: audio WAV (instant) → Obsidian text (needs TTS) → full pipeline (JIRA+Ollama+TTS).

## Architecture

```
saymo/
├── cli.py                    # Click CLI, all commands, 3-level cache logic
├── config.py                 # Dataclass config with ${ENV_VAR} substitution
├── tui.py                    # Interactive dashboard (Rich Live + threading)
├── wizard.py                 # Interactive setup wizard
├── glip_control.py           # AppleScript + JS injection for Chrome automation
├── providers/
│   ├── _chrome_base.py       # Base: Chrome tab detection, mute toggle
│   ├── glip.py               # Glip (+ JS mic switch override)
│   ├── zoom.py               # Zoom Web (Alt+A)
│   ├── google_meet.py        # Google Meet (Cmd+D)
│   ├── ms_teams.py           # MS Teams (Cmd+Shift+M)
│   ├── telegram.py           # Telegram Web (Space)
│   ├── telemost.py           # Yandex Telemost (M)
│   ├── vk_teams.py           # VK Teams (M)
│   ├── mts_link.py           # MTS Link (Space)
│   └── factory.py            # get_provider("zoom") factory
├── jira_source/
│   ├── confluence_tasks.py   # Personal + team task fetch (same JQL as update_confluence.py)
│   └── tasks.py              # Simple JIRA query wrapper
├── speech/
│   ├── ollama_composer.py    # Standup text via Ollama (personal + team prompts)
│   └── composer.py           # Claude API composer (cloud fallback)
├── tts/
│   ├── coqui_clone.py        # XTTS v2 voice cloning
│   ├── piper_tts.py          # Piper TTS (fast, local)
│   ├── macos_say.py          # macOS say (builtin fallback)
│   ├── openai_tts.py         # OpenAI TTS (cloud)
│   ├── text_normalizer.py    # Abbreviations, numbers, IT terms → phonetics
│   └── base.py               # TTSEngine protocol
├── audio/
│   ├── capture.py            # Overlapping sliding window (4s/2s overlap)
│   ├── playback.py           # Play to single device
│   ├── multi_play.py         # Play to multiple devices simultaneously
│   ├── devices.py            # Device discovery
│   └── recorder.py           # Voice sample recorder
├── stt/
│   └── whisper_local.py      # faster-whisper (local, no API)
├── analysis/
│   └── turn_detector.py      # Fuzzy name detection with cooldown
└── obsidian/
    └── daily_notes.py        # Read Obsidian vault daily notes
```

## Config (config.yaml)

Key sections:
- `user.name_variants` — trigger phrases for auto mode
- `audio.playback_device / monitor_device` — headphones + BlackHole routing
- `tts.engine` — `coqui_clone` | `piper` | `macos_say` | `openai`
- `speech.source` — `confluence` | `obsidian` | `jira`
- `speech.composer` — `ollama` | `anthropic`
- `team` — JIRA usernames → display names for scrum mode
- `meetings.*` — profiles with provider, trigger phrases, team flag

## Adding a New Call Provider

```python
# saymo/providers/new_app.py
from saymo.providers._chrome_base import ChromeCallProvider

class NewAppProvider(ChromeCallProvider):
    name = "new_app"
    url_pattern = "calls.example.com"
    mute_key = "m"
```

Then add to `saymo/providers/factory.py` PROVIDERS dict.

## Adding Team Members

Edit `team:` section in `config.yaml`:
```yaml
team:
  username: "Display Name"
```

## Adding Abbreviations

Edit `ABBREV_MAP` in `saymo/tts/text_normalizer.py`:
```python
"ABBR": "pronunciation",
```

## Audio Routing

```
Saymo TTS → BlackHole 2ch → Call mic input (others hear you)
          → Plantronics   → Headphones (you hear yourself)

Call speakers → Multi-Output Device → Plantronics (you hear others)
                                    → BlackHole 16ch (auto mode listens)
```

## Key Dependencies

- macOS arm64 (Apple Silicon, NOT Rosetta)
- Python 3.11+, PyTorch 2.6+
- Ollama + qwen2.5-coder:7b model
- brew: ffmpeg, blackhole-2ch, blackhole-16ch, portaudio
- Chrome with "Allow JavaScript from Apple Events" enabled
