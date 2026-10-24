# Product Requirements Document: Saymo

## 1. Introduction

Saymo is a fully local AI voice assistant for macOS that listens for the user's name on video calls, composes a concise verbal update from configurable data sources (Obsidian, Jira, plain text), and speaks it through a voice-cloned synthetic voice — all on-device with zero cloud dependencies.

## 2. Problem Statement

Engineering teams spend 5-15 minutes per standup passively listening while each member gives a verbal status update. For individuals across multiple teams or meetings, this time compounds significantly. Existing solutions either require cloud TTS (privacy concern), lack voice cloning (sounds robotic), require manual triggering, or fail to integrate with the call platform's mute/unmute lifecycle — forcing the user to context-switch and announce their own automated speech.

## 3. User Personas

| Persona | Description | Key Need |
|---------|-------------|----------|
| **Senior Engineer (Primary)** | 3-5 daily standups across teams, Obsidian/Jira user, privacy-conscious | Automated, cloned-voice standup replies with zero cloud exposure |
| **Tech Lead** | Runs standups, needs to hear team but automate own update | Fast cache-hit replies, team-scrum mode with rollup |
| **Scrum Master** | Facilitates multiple scrums, tracks blockers | Configurable meeting profiles, quick mode for ad-hoc notes |
| **Privacy-First User** | Corp policy prohibits cloud STT/TTS | Fully local pipeline, no API keys required |

## 4. Functional Requirements

### 4.1 CLI & Configuration

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| F1.1 | Interactive setup wizard (`saymo setup`) | P0 | Guide through name, devices, TTS engine, call provider, data source |
| F1.2 | YAML config with env-var interpolation | P0 | `config.yaml` with `${VAR}` secret injection |
| F1.3 | Multiple named meeting profiles | P0 | Each profile: provider, trigger phrases, voice, source plugin, live-loop params |
| F1.4 | CLI commands for all major operations | P0 | `auto`, `speak`, `prepare`, `rehearsal`, `dashboard`, `dry-run` |

### 4.2 Voice Cloning & TTS

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| F2.1 | Zero-shot voice cloning (XTTS v2) | P0 | ~5 min setup, single 30s sample |
| F2.2 | Fine-tuned voice cloning (XTTS + RVC v2) | P1 | ~2-3h training, 9-10/10 similarity |
| F2.3 | One-stage Russian voice cloning (F5-TTS) | P1 | ~10 min setup, Russian-optimized |
| F2.4 | MLX-native voice cloning (Qwen3-TTS LoRA) | P2 | Apple Silicon GPU-accelerated |
| F2.5 | CPU-friendly fallback TTS (Piper, macOS `say`) | P0 | Always-available fallback engines |
| F2.6 | Voice profile system with approval gating | P0 | Init → Check → Approve → Call-ready lifecycle |
| F2.7 | Text normalization for TTS | P0 | Abbreviation expansion, number formatting, version strings |
| F2.8 | Naturalness presets (speed, temperature, repetition penalty) | P1 | Tunable per engine, documented in `NATURAL_PRESET` |
| F2.9 | Breath-sample insertion for natural pauses | P2 | Load synthetic breath audio between sentences |

### 4.3 Auto-Mode (Live Call Listening)

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| F3.1 | Capture call audio from BlackHole virtual device | P0 | 16ch capture, 4s overlapping windows |
| F3.2 | Local STT via faster-whisper (large-v3) | P0 | CPU int8, optional GPU |
| F3.3 | Fuzzy name detection across transcript chunks | P0 | Configurable name variants + fuzzy expansions for STT errors |
| F3.4 | Addressing classification (direct question, handoff, narrated mention) | P0 | Regex patterns → `AddressingDecision` with confidence |
| F3.5 | Double-trigger confirmation window | P0 | Second name mention within 6s confirms intent |
| F3.6 | 45s cooldown after each auto-speech | P0 | Prevents re-trigger loops |
| F3.7 | Optional LLM intent classifier (Ollama) | P1 | Catch semantic rephrasings missed by keyword match |
| F3.8 | Live-assist classifier (can only _downgrade_ decisions) | P1 | Safety boundary: never force-speak, only skip |

### 4.4 Response Cache

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| F4.1 | Pre-synthesized answers for common standup questions | P0 | Tier-A cache for CPU-bound <500ms replies |
| F4.2 | Cache-keyword matching against transcript | P0 | Match transcript to cache intent keys |
| F4.3 | Configurable response library with intent mapping | P0 | YAML-defined: "status" → "I'm working on X", "blockers" → "No blockers" |
| F4.4 | Cache metadata (WAV sidecar JSON) | P1 | Track voice profile, engine, duration per cache entry |
| F4.5 | Cache status command (`saymo cache-status`) | P1 | Show hits/misses, most-used intents |

### 4.5 Live Fallback Q&A

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| F5.1 | On cache miss, generate answer via Ollama + TTS | P1 | <5s target for live generation |
| F5.2 | Q&A prompt produces 1-3 sentence answers, ~15s spoken | P0 | Never reveals being AI |
| F5.3 | Answer-standalone questions only (no conversation) | P0 | Q&A mode, not chat |

### 4.6 Call Provider Automation

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| F6.1 | Chrome CDP-based provider detection | P0 | Find meeting tab, detect provider type |
| F6.2 | Unmute → Speak → Mute sequence | P0 | Press Space, route audio, re-mute |
| F6.3 | Provider-specific JS injection | P0 | Per-provider scripts for 8 platforms |
| F6.4 | Provider latency measurement | P1 | `saymo provider-latency` command |
| F6.5 | Provider audio readiness check | P1 | Validate BlackHole routing per provider |

### 4.7 Data Sources & Composition

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| F7.1 | Obsidian vault reader | P0 | Read yesterday/today daily notes |
| F7.2 | Jira task fetcher (JQL) | P1 | Fetch assigned tasks, worklog |
| F7.3 | Team-scrum Jira (all members) | P2 | Rollup all team members' tasks |
| F7.4 | Plain-text file source | P0 | Read from `~/.saymo/summary.md` |
| F7.5 | Ollama standup composer | P0 | Compose notes into natural 1-paragraph speech |
| F7.6 | Optional Anthropic composer | P1 | Cloud fallback for composition (voice stays local) |
| F7.7 | Brief-expansion mode (`saymo quick`) | P1 | Type brief notes → Ollama expands → speaks |

### 4.8 Safety & Controls

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| F8.1 | Global hotkeys (speak, stop, toggle, takeover) | P0 | Cmd+Shift+S/X/M/U |
| F8.2 | Handbrake panel (`saymo live-control`) | P0 | Stop auto-answer, manual takeover, hard disable |
| F8.3 | Rehearsal mode (`saymo rehearsal`) | P0 | Dry-run with scorecard before live call |
| F8.4 | Max speech duration timeout | P0 | Hard stop after N seconds |
| F8.5 | LaunchAgent for background daemon | P1 | Per-profile autostart + heartbeat |
| F8.6 | Safety soak gate (`saymo safety-soak`) | P1 | Aggregate scorecards, compare against baseline |
| F8.7 | Session scorecard (`saymo session-scorecard`) | P1 | Sanitized reliability report per session |

### 4.9 Training & Evaluation

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| F9.1 | Guided training sample recording | P0 | `saymo train-prepare` with category prompts |
| F9.2 | Dataset builder with ground-truth transcripts | P0 | `saymo train-rebuild`, metadata.csv |
| F9.3 | XTTS v2 fine-tuning (`saymo train-voice`) | P1 | Configurable epochs, batch size |
| F9.4 | Qwen3-TTS LoRA fine-tuning (`saymo train-qwen3`) | P2 | LoRA rank, scale, lr |
| F9.5 | A/B evaluation (`saymo train-eval`) | P1 | Compare baseline vs fine-tuned, blind sentences |
| F9.6 | Training status dashboard (`saymo train-status`) | P1 | Dataset size, model paths, last eval |

## 5. Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR1 | E2E latency (cache hit) | <500ms | From name detected → audio playing |
| NFR2 | E2E latency (live fallback) | <5s | From name detected → audio playing |
| NFR3 | Voice similarity (fine-tuned) | >= 8/10 | Blind A/B test |
| NFR4 | Voice similarity (zero-shot) | >= 6/10 | Blind A/B test |
| NFR5 | Cloud API calls (default config) | 0 | No outbound to cloud STT/TTS/LLM |
| NFR6 | False-positive auto-speech rate | 0 per 100 call-minutes | After double-trigger enabled |
| NFR7 | First-time setup time | <30 min | From `git clone` → `saymo setup` done |
| NFR8 | Config validation | Startup | Invalid config exits with clear error |
| NFR9 | Hotkey response latency | <200ms | Global hotkey → action starts |

## 6. User Flows

### 6.1 First-Time Setup
```
install.sh → saymo setup (wizard) → saymo record-voice → saymo voice-profile init
→ saymo voice-profile check → saymo train-voice / --engine=coqui_clone → saymo test-tts
→ saymo prepare → saymo rehearsal → saymo auto
```

### 6.2 Daily Standup (Auto-Mode)
```
saymo auto --profile=personal
  ├── Chrome detects meeting tab (Glip/Zoom/etc.)
  ├── AudioCapture starts 4s overlapping windows
  ├── faster-whisper transcribes each chunk
  ├── TurnDetector checks for name + fuzzy variants
  ├── AddressingClassifier: was it a direct question?
  ├── Double-trigger within 6s? → confirm
  ├── ResponseCache: keyword match? → play cached audio
  │   └── Cache miss? → Ollama compose + TTS → play
  ├── Provider: unmute → play → mute
  └── 45s cooldown
```

### 6.3 Manual Speak
```
saymo speak --profile=personal --source=obsidian
  └── Reads today's Obsidian notes → Ollama composes → TTS → plays via provider
```

## 7. Edge Cases & Error Handling

| Scenario | Handling |
|----------|----------|
| Ollama not running | `check_ollama_health()` — graceful error with suggestion to start Ollama |
| No BlackHole device | `saymo test-devices` — detect missing BlackHole, guide install |
| Provider tab not found | Chrome CDP scan → retry → clear error: "No meeting tab found for {provider}" |
| Voice sample too short | Reject <10s samples, suggest `saymo record-voice --duration 30` |
| Model download interrupted | Resume on retry, clear error on disk space |
| Transcription confidence low | Skip trigger, log debug warning |
| Multiple names in transcript | Classify each addressing independently, highest confidence wins |
| Cache miss + live fallback slow | Fallback to generic "please repeat" audio after N seconds |
| Config env var not set | Load-time error with missing var name, never substitute empty string |
| Hotkey conflict (macOS) | `saymo hotkey-doctor` — diagnose and suggest reassigning |

## 8. Feature Prioritization

### MVP (P0)
- CLI with `setup`, `auto`, `speak`, `prepare`, `rehearsal`
- YAML config with env-var interpolation and meeting profiles | - Zero-shot XTTS voice cloning + Piper/macOS `say` fallback
- Local STT (faster-whisperarge-v3)
- urz name etection + addessing classification + double-trigger
- Response cache with pre-synthesized standup intents
- BlackHole capture/playback routing
- Chrome CDP provider automation (Glip, Zoom)
- Safety hotkeys (speak, stop, toggle, takeover)

### v2 (P1)
- ine-tuned XTTS + RVC v2 pipeline
- ive fallback (Ollama + TTS)
- Jira plugin + team-scrum mode | - ive-assist classifier (downgrade only)
- Qwen3-TTS clning (MLX)
- LaunchAgent daemo | - all providers (Google Meet, MS Teams, Telegram, etc.)
- A/B evaluation (`train-eval`)

### v3 (P2)
- F5-TTS Russian one-stage clning
- Quality evaluator + regression replay
- Safety soak gate + session scorecards
- Ad-hoc dark mode / "saymo quick" expasion | - Provider latency measurement

## 9. Dependencies & Contraints

### Runtime Dependencies
- **macOS** (Apple Silicon arm64) — only supported OS/arch
- **BlackHole** virtual audio driver → `brew install blackhole-16ch blackhole-2ch`
- **Ollama** (optional, for live fallback) → `brew install ollama`
- **faster-whisper** → Python model download (~3GB for large-v3)
- **Chrome** with remote DevTools debugging port open
- **XTTS v2** model files (~2GB download on first use)

### Build Dependencies
- Python 3.11+
- `uv` package manager
- Homebrew for system deps

### Constraints
- All on-device: no cloud TTS/STT paths in default configuration
- Single-speaker output (user's cloned voice only)
- Passive Q&A mode: never intiates speech, only responds to name
- macOS-ony: no cross-platform support planned

## 10. Acceptance Criteria

1. `bash install.sh` completes without errors on a clean macOS Sonoma/Sequoia machine
2. `saymo setup` walks through name, devices, TTS engine, provider — valid config produced
3. `saymo record-voice --duration 30` saves a playable 30s WAV
4. `saymo test-tts "Hello, this is my cloned voice"` plays audible speech
5. `saymo prepare --profile=personal` produces standup text + cache audio files
6. `saymo rehearsal --provider=glip` reports pass/fail with scorecard
7. `saymo auto --profile=personal` detects meeting tab, captures audio, does not false-trigger in 5 min of silence
8. Voice similarity >= 6/10 (zero-shot) measured by blind A/B
9. Zero cloud API calls in `config.example.yaml` default config
10. `uv run pytest` passes full test suite