# Saymo — Product Requirements Document

## Overview

Saymo is a fully local AI voice assistant for macOS. It pulls optional context from plugin sources (tracker, notes, files), composes natural speech with a local LLM, synthesizes it in the user's cloned voice, and delivers audio into any live call — all without cloud APIs.

## Core Architecture

```
┌──────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│ Source Plugin │────▸│ LLM Composer │────▸│ Text Normalizer│────▸│  TTS Engine  │
│ (fetch tasks) │     │ (Ollama)     │     │ (abbrevs, nums)│     │ (XTTS clone) │
└──────────────┘     └──────────────┘     └────────────────┘     └──────┬───────┘
                                                                        │
┌──────────────┐     ┌──────────────┐     ┌────────────────┐            │
│ Call Provider │◂────│ Auto Trigger │◂────│  STT (Whisper) │      Audio bytes
│ (mute/unmute) │     │ (name detect)│     │ (capture call) │            │
└──────┬───────┘     └──────────────┘     └────────────────┘            │
       │                                                                │
       ▼                                                                ▼
  BlackHole 2ch ──────────────────────────────────────────────── Audio output
  (virtual mic)                                                 + monitor
```

## Plugin System — Source Plugins

### What it does
Source plugins fetch standup content (tasks, notes, summaries) from external systems. Plugins are **auto-discovered** by scanning `saymo/plugins/` directory.

### Existing plugins

| Plugin | `name` | Description |
|--------|--------|-------------|
| `confluence.py` | `confluence` | JIRA tasks via confluence JQL (personal) |
| `confluence_team.py` | `confluence_team` | JIRA tasks for all team members |
| `obsidian.py` | `obsidian` | Obsidian vault daily notes (markdown) |
| `jira_simple.py` | `jira` | Simple JIRA assignee query |
| `file_summary.py` | `file` | Read pre-written text file |

### How to create a new plugin

Create a file in `saymo/plugins/` with a class that has:

```python
# saymo/plugins/my_source.py

class MySource:
    name = "my_source"                    # Used in config.yaml: speech.source
    description = "Fetch from My System"  # Shown in saymo list-plugins

    async def fetch(self, config) -> dict | None:
        """Fetch standup content.

        Args:
            config: SaymoConfig instance (access config.jira, config.obsidian, etc.)

        Returns:
            dict with keys:
                yesterday: str | None — what was done (plain text, one item per line)
                today: str | None — what's planned
                yesterday_date: str — date string for display
                today_date: str — date string for display
            Or None if no data available.
        """
        # Your fetch logic here
        return {
            "yesterday": "- Completed task A\n- Fixed bug B",
            "today": "- Working on feature C\n- Review PR D",
            "yesterday_date": "2026-04-16",
            "today_date": "2026-04-17",
        }
```

That's it. Drop the file in `saymo/plugins/` — it's auto-discovered on next run.

### Plugin ideas to implement

| Plugin | Source | Notes |
|--------|--------|-------|
| `github_prs.py` | GitHub API | PRs created/reviewed/merged yesterday |
| `gitlab_mrs.py` | GitLab API | Merge requests activity |
| `linear.py` | Linear API | Tasks from Linear project management |
| `notion.py` | Notion API | Daily notes from Notion workspace |
| `todoist.py` | Todoist API | Completed/planned tasks |
| `google_calendar.py` | Google Calendar | Yesterday's meetings + today's schedule |
| `slack_activity.py` | Slack API | Messages/threads from standup channels |
| `git_log.py` | Local git | Commits from yesterday in configured repos |
| `trello.py` | Trello API | Cards moved/updated |
| `youtrack.py` | YouTrack API | JetBrains issue tracker |
| `clickup.py` | ClickUp API | Tasks and time tracking |
| `asana.py` | Asana API | Tasks completed/assigned |
| `composite.py` | Multiple | Combine output from several plugins |

### Config integration

In `config.yaml`:
```yaml
speech:
  source: "my_source"    # matches plugin name

# Add plugin-specific config sections as needed:
my_source:
  api_url: "https://..."
  token: "${MY_SOURCE_TOKEN}"
```

Access in plugin: plugins receive the full `SaymoConfig` object. For custom config sections, read from the YAML directly:
```python
import yaml
from pathlib import Path

cfg = yaml.safe_load(Path("config.yaml").read_text())
my_config = cfg.get("my_source", {})
```

### Testing a plugin
```bash
# Verify plugin is discovered:
saymo list-plugins

# Test fetch (compose text without audio):
saymo test-compose --source my_source

# Full test with audio:
saymo prepare --source my_source
saymo speak
```

---

## Provider System — Call Providers

### What it does
Call providers automate interaction with video call apps: find the call window/tab, toggle mute, switch microphone.

### Existing providers

| Provider | `name` | URL Pattern | Mute Key | Status |
|----------|--------|-------------|----------|--------|
| Glip (RingCentral) | `glip` | `v.ringcentral.com/conf` | Space | Full (JS mic switch) |
| Zoom | `zoom` | `app.zoom.us` | Alt+A | Stub |
| Google Meet | `google_meet` | `meet.google.com` | Cmd+D | Stub |
| Microsoft Teams | `ms_teams` | `teams.microsoft.com` | Cmd+Shift+M | Stub |
| Telegram | `telegram` | `web.telegram.org` | Space | Stub |
| Yandex Telemost | `telemost` | `telemost.yandex.ru` | M | Stub |
| VK Teams | `vk_teams` | `teams.vk.com` | M | Stub |
| MTS Link | `mts_link` | `mts-link.ru` | Space | Stub |

### How to create a new provider

All providers extend `ChromeCallProvider` which handles Chrome tab detection, activation, and mute toggle.

```python
# saymo/providers/my_app.py
from saymo.providers._chrome_base import ChromeCallProvider

class MyAppProvider(ChromeCallProvider):
    name = "my_app"
    url_pattern = "app.myservice.com"   # Chrome tab URL substring to find
    mute_key = "m"                      # Key to press for mute toggle
    mute_modifiers = ""                 # Optional: "command down", "command down, shift down"
```

Then register in `saymo/providers/factory.py`:
```python
from saymo.providers.my_app import MyAppProvider

PROVIDERS = {
    ...
    "my_app": MyAppProvider,
}
```

### ChromeCallProvider base class methods

| Method | What it does | Override needed? |
|--------|-------------|------------------|
| `check_ready()` | Find Chrome tab matching `url_pattern` | No |
| `activate_meeting()` | Bring tab to focus | No |
| `toggle_mute()` | Press `mute_key` with `mute_modifiers` | No |
| `switch_mic(device)` | Switch mic in the call UI | Yes (provider-specific) |
| `get_previous_app()` | Get current foreground app name | No |
| `activate_app(name)` | Restore focus to an app | No |

Override `switch_mic()` if the provider supports programmatic mic switching (via JS injection or accessibility). See `glip.py` for reference.

### Provider implementation levels

**Level 1 — Basic (5 lines):** URL pattern + mute key. Tab detection and mute toggle work. Mic must be switched manually.

**Level 2 — JS mic switch:** Override `switch_mic()` with JavaScript that clicks through the provider's audio settings UI. Requires knowing the DOM structure.

**Level 3 — Full API:** Use the provider's API for mute/unmute and mic switch. Most providers don't support this.

### Testing a provider
```bash
# Verify provider is registered:
saymo list-plugins

# Test tab detection (open the call in Chrome first):
python3 -c "
from saymo.providers.factory import get_provider
p = get_provider('my_app')
print(p.check_ready())
"

# Full test:
saymo speak -p my_meeting --glip
```

---

## Text Normalizer

### What it does
Converts written text to TTS-friendly pronunciation. Runs automatically before any TTS engine.

### File: `saymo/tts/text_normalizer.py`

### Abbreviation map (`ABBREV_MAP`)
Generic IT/DevOps vocabulary ships in source. Example entries:
```python
"QA": "кью-эй",
"ETL": "и-ти-эл",
"API": "эй-пи-ай",
"smoke": "смоук",
"stage": "стейдж",
```

### Rules applied (in order)
1. Remove build versions (long numeric stamps, e.g. `v.2604101636`)
2. Remove tracker IDs (regex `FOO-123:`)
3. Remove standalone long numbers (8+ digits)
4. Expand abbreviations from `ABBREV_MAP` + `config.vocabulary.abbreviations`
5. Expand version numbers (`1.0.0` → `один точка ноль точка ноль`)
6. Expand short numbers to Russian words (`15` → `пятнадцать`)
7. Strip markdown artifacts (`---`, `**`, `#`)

### Adding project-specific terms
Do **not** edit source. Add them to your `config.yaml`:
```yaml
vocabulary:
  abbreviations:
    NEW_TERM: "произношение-по-русски"
```

---

## Meeting Profiles

### Config structure (`config.yaml`)
```yaml
meetings:
  profile_name:
    description: "Human-readable description"
    provider: "glip"              # Call provider name
    team: false                   # Personal or team report
    source: "confluence"          # Source plugin name
    trigger_phrases:              # Words for auto-mode trigger
      - "{user_name}"
      - "your team"
```

### Trigger phrases
Used by `saymo auto` mode. When faster-whisper transcription contains any of these phrases, Saymo auto-speaks. Supports:
- Exact match: `"Alex"`
- Regex patterns: `"Alex.*очередь"`
- Fuzzy variants (supplied via `config.vocabulary.fuzzy_expansions`)

---

## TTS Engines

| Engine | Config name | Local | Voice clone | Speed |
|--------|-------------|-------|-------------|-------|
| Coqui XTTS v2 | `coqui_clone` | Yes | Yes | ~30-90s |
| Piper | `piper` | Yes | No | <1s |
| macOS say | `macos_say` | Yes | No | <1s |
| OpenAI TTS | `openai` | No | No | ~2s |

Voice sample: `~/.saymo/voice_samples/voice_sample.wav` (5 min recommended).

---

## Three-Level Cache

```
~/.saymo/audio_cache/YYYY-MM-DD.wav       → instant playback (~2s)
    ↓ cache miss
Obsidian daily note "## Standup Summary"  → needs TTS (~30s)
    ↓ cache miss
Full pipeline: plugin.fetch → Ollama → TTS → cache  (~60s)
```

Audio cache auto-rotates after 7 days.

---

## Audio Routing

```
Saymo TTS → BlackHole 2ch  → Call mic (others hear)
          → Monitor device  → Headphones (you hear yourself)

Call audio → Multi-Output Device → Headphones (you hear others)
                                 → BlackHole 16ch (auto mode captures)
```

### Requirements
- `brew install blackhole-2ch blackhole-16ch`
- Multi-Output Device in Audio MIDI Setup: headphones (master) + BlackHole 16ch (drift correction)
- Chrome: View → Developer → Allow JavaScript from Apple Events

---

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `saymo setup` | Interactive wizard (name, devices, meetings) |
| `saymo prepare -p PROFILE` | Fetch tasks, compose, pre-generate audio |
| `saymo speak --glip` | Play cached audio into call |
| `saymo auto -p PROFILE` | Listen for trigger, auto-speak |
| `saymo review` | Review audio sentence-by-sentence |
| `saymo record-voice -d 300` | Record 5-min voice sample |
| `saymo dashboard` | Interactive TUI |
| `saymo list-plugins` | Show plugins and providers |
| `saymo test-*` | Test individual components |

---

## Dependencies

### Core (always installed)
`sounddevice`, `soundfile`, `numpy`, `click`, `rich`, `pynput`, `pyyaml`, `httpx`, `jira`

### Optional groups (`pyproject.toml`)
- `[tts]`: `torch`, `torchaudio`, `coqui-tts[codec]`, `piper-tts`, `scipy`, `transformers`
- `[stt]`: `faster-whisper`
- `[cloud]`: `anthropic`, `openai`, `deepgram-sdk`, `aiohttp`
- `[all]`: everything

### System
- macOS arm64, Python 3.11+, Homebrew
- `brew install ffmpeg portaudio blackhole-2ch blackhole-16ch`
- Ollama + `qwen2.5-coder:7b` model
- Chrome with JS from Apple Events enabled
