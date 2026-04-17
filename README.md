# Saymo — AI Standup Automation

Fully local AI assistant for standup meetings. Fetches JIRA tasks, composes summary via Ollama, speaks in your cloned voice — all without cloud APIs.

**Supports 8 call providers:** Glip, Zoom, Google Meet, MS Teams, Telegram, Yandex Telemost, VK Teams, MTS Link.

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4) — **arm64 terminal, NOT Rosetta**
- Python 3.11+
- Homebrew
- Google Chrome
- ~10 GB free disk space

## Quick Install

```bash
git clone <repo-url> saymo && cd saymo
./install.sh
```

The installer handles everything: brew deps, Python packages (via uv or pip), Ollama check, Piper voice model, Chrome permissions.

## First Time Setup

```bash
# 1. Interactive wizard — configure name, audio devices, meeting profiles:
saymo setup

# 2. Record your voice (5 minutes, speak naturally):
saymo record-voice -d 300

# 3. Verify audio devices:
saymo test-devices

# 4. Test TTS:
saymo test-tts "Привет, это тест"
```

### Audio Routing (one-time, manual)

```
┌─────────────────────────────────────────────────────────────┐
│                     Audio MIDI Setup                        │
│                                                             │
│  Create "Multi-Output Device":                              │
│    ✓ Plantronics / headphones  (master, no drift correction)│
│    ✓ BlackHole 16ch            (drift correction ON)        │
│                                                             │
│  In your call app (Glip/Zoom/Meet/etc):                     │
│    Microphone → BlackHole 2ch                               │
│    Speakers   → Multi-Output Device                         │
└─────────────────────────────────────────────────────────────┘
```

## Daily Usage

```bash
# ═══ Before meeting (5 min) ═══
saymo prepare -p standup        # Personal standup
saymo prepare -p scrum          # Team report (you + teammates)
saymo review                    # Optional: fix audio quality

# ═══ During meeting ═══
saymo speak --glip              # Manual trigger — instant playback
saymo auto -p standup           # Full auto — listens for your name, speaks when called

# ═══ Quick shortcuts ═══
saymo speak -p scrum --glip     # Team report in Glip
saymo auto -p scrum --mic       # Test auto mode with your mic
saymo dashboard                 # Interactive TUI
```

## Meeting Profiles

Configure in `config.yaml` → `meetings:` section:

```yaml
meetings:
  standup:
    provider: "glip"          # glip, zoom, google_meet, teams, telegram, telemost, vk, mts_link
    team: false               # personal or team report
    source: "confluence"      # confluence, obsidian, jira
    trigger_phrases:          # words that trigger auto-speak
      - "Михаил"
      - "Миша"

  scrum:
    provider: "glip"
    team: true
    trigger_phrases:
      - "QA"
      - "QA team"
      - "Михаил"
```

## Porting to Another Mac

### What to copy:
```bash
# 1. The project itself
git clone <repo-url> saymo

# 2. Voice sample (your recorded voice)
mkdir -p ~/.saymo/voice_samples
scp old-mac:~/.saymo/voice_samples/voice_sample.wav ~/.saymo/voice_samples/

# 3. Config with your settings
# (already in repo, edit config.yaml for new machine paths)
```

### On the new Mac:
```bash
# Ensure arm64 terminal (NOT Rosetta!)
uname -m  # must show arm64

# Install everything
cd saymo && ./install.sh

# Install Ollama if not present
brew install ollama
ollama pull qwen2.5-coder:7b

# Configure for your setup
saymo setup

# Set up audio routing in Audio MIDI Setup (see above)

# Test
saymo test-devices
saymo test-tts "Тест"
saymo prepare -p standup
saymo speak
```

### Environment-specific settings in `config.yaml`:
```yaml
# Update these paths for the new machine:
audio:
  playback_device: "Your Headphones"     # saymo test-devices to find name
  monitor_device: "Your Headphones"
  capture_device: "BlackHole 16ch"

obsidian:
  vault_path: "/Users/YOUR_USERNAME/Documents/Obsidian Vault"

jira:
  selfhelper_path: "/path/to/selfhelper"  # or set use_selfhelper_config: false
```

### Files stored outside the repo:
```
~/.saymo/
├── voice_samples/
│   └── voice_sample.wav          # Your 5-min voice recording (~13 MB)
├── piper_models/
│   └── ru_RU-dmitri-medium.onnx  # Piper Russian voice (~60 MB, auto-downloaded)
└── audio_cache/
    ├── 2026-04-17.wav            # Today's cached standup audio (auto-rotated 7 days)
    └── 2026-04-17-team.wav       # Today's cached team audio
```

## Tech Stack

| Component | Technology | Size |
|-----------|-----------|------|
| LLM | Ollama (qwen2.5-coder:7b) | 4.4 GB |
| Voice Clone | Coqui TTS XTTS v2 | ~2 GB |
| STT | faster-whisper (small) | ~500 MB |
| TTS Fallback | Piper (ru_RU-dmitri) | 60 MB |
| Audio | BlackHole 2ch + 16ch | — |
| Automation | AppleScript + Chrome JS | — |

## Project Structure

```
saymo/
├── install.sh              # Full setup script
├── config.yaml             # All settings, meeting profiles, team members
├── pyproject.toml           # Dependencies (core, [tts], [stt], [cloud])
├── saymo/                  # Python package
│   ├── cli.py              # All CLI commands
│   ├── providers/          # 8 call providers (Chrome-based)
│   ├── tts/                # 4 TTS engines + text normalizer
│   ├── stt/                # Local Whisper STT
│   ├── speech/             # Ollama/Claude text composition
│   ├── audio/              # Capture, playback, multi-device, recorder
│   ├── jira_source/        # JIRA task fetching
│   ├── analysis/           # Name trigger detection
│   ├── plugins/            # Source plugins (Confluence, Obsidian, JIRA, file)
│   └── obsidian/           # Daily notes reader
├── docs/PLUGINS.md         # How to add a source plugin / call provider
├── docs/adr/               # 8 Architecture Decision Records
├── voice_reading_script.md # Script for recording voice sample
└── CLAUDE.md               # Instructions for Claude Code
```

## Extending Saymo

Add a new task source (Notion, Linear, GitHub) or a new meeting app — see **[docs/PLUGINS.md](docs/PLUGINS.md)** for copy-pasteable examples.
