# Architecture: Saymo

## 1. System Overview

Saymo is a **single-process, event-loop-driven** macOS application. All components run within one Python process using `asyncio` for concurrency. CPU-bound work (STT, TTS, LLM inference) is offloaded to threads via `asyncio.to_thread`. Inter-process communication uses file-based JSON protocols (no sockets or pipes).

```
┌────────────────────────────────────────────────────────────────────────────┐
│  macOS (Apple Silicon arm64)                                                │
│                                                                            │
│  ┌─────────────────────┐    ┌───────────────────────────────────────────┐  │
│  │  saymo process       │    │  saymo call-control daemon                │  │
│  │  (auto / speak / ...) │    │  (LaunchAgent, per-profile)               │  │
│  │                      │    │                                           │  │
│  │  asyncio event loop  │    │  pynput GlobalHotKeys                     │  │
│  │  ┌───────┬───────┐  │    │  commands.jsonl → auto process            │  │
│  │  │transc │trigger│  │    └──────────────┬────────────────────────────┘  │
│  │  │_loop  │_loop  │  │                   │ JSON file protocol            │
│  │  └───┬───┴───┬───┘  │                   │                               │
│  │      │       │       │    ┌──────────────▼────────────────────────┐     │
│  │      ▼       ▼       │    │  ~/.saymo/live_control/<profile>/     │     │
│  │  STT       TTS       │    │  ├── state.json        (LiveControl) │     │
│  │  (whisper) (engine)  │    │  ├── commands.jsonl     (command Q)   │     │
│  │      │       │       │    │  ├── audit.jsonl        (audit trail) │     │
│  │      ▼       ▼       │    │  └── daemon-heartbeat   (liveness)    │     │
│  │  Audio     Audio     │    └───────────────────────────────────────┘     │
│  │  Capture   Playback  │                                                 │
│  │  (16kHz)   (24kHz)   │    ┌───────────────────────────────────────┐     │
│  └──────┬───────┬───────┘    │  External Dependencies                 │     │
│         │       │            │  ├── BlackHole 16ch/2ch (virtual audio) │     │
│         ▼       ▼            │  ├── Google Chrome + AppleScript       │     │
│  ┌─────────┐ ┌──────────┐   │  ├── Ollama (optional, live fallback)  │     │
│  │BlackHole│ │BlackHole │   │  ├── faster-whisper models (STT)       │     │
│  │ 16ch    │ │ 2ch      │   │  └── TTS model files (XTTS/F5/Qwen3)  │     │
│  │(capture)│ │(playback)│   └───────────────────────────────────────┘     │
│  └────┬────┘ └────┬─────┘                                                 │
│       │           │                                                       │
│       ▼           ▼                                                       │
│  ┌──────────┐ ┌──────────┐                                               │
│  │ Call App │ │ Chrome   │                                               │
│  │ (audio)  │ │ (provider│                                               │
│  │          │ │  control)│                                               │
│  └──────────┘ └──────────┘                                               │
└────────────────────────────────────────────────────────────────────────────┘
```

## 2. Module Dependency Graph

```
commands/  (top-level integration — imports everything)
  ├── core.py       — auto, speak, prepare, dashboard, live-control
  ├── tests.py      — diagnostics (test-devices, hotkey-doctor, preflight)
  ├── voice_train.py — training pipeline (train-voice, train-eval)
  ├── voice_clone.py — voice profile management, F5 presets
  ├── call_ready.py  — launch readiness checks
  ├── dry_run.py     — pre-flight dry-run with evidence
  └── call_control.py — daemon lifecycle, probe, LaunchAgent

analysis/  (central integration hub — depends on most modules)
  ├── addressing.py         — regex-based addressing classification
  ├── turn_detector.py      — fuzzy keyword name matching
  ├── response_cache.py     — Tier-A pre-synthesized answer library
  ├── realtime_gate.py      — launch + runtime safety gates
  ├── realtime_policy.py    — response resolution (cache → live fallback → block)
  ├── realtime_events.py    — structured decision logging
  ├── live_control.py       — JSON file protocol, action catalog, state, audit
  ├── control_daemon.py     — pynput hotkey listener + heartbeat
  ├── trigger_classifier.py — optional ML classifier (Naive Bayes, shadow mode)
  ├── trigger_readiness.py  — classifier training readiness + live-assist gating
  ├── launch_readiness.py   — 15-point pre-flight checklist
  ├── launch_sources.py     — source plugin readiness
  ├── launch_cache.py       — cache validation
  ├── launch_agent.py       — LaunchAgent plist builder
  ├── launch_evidence.py    — launch evidence artifact (JSON)
  ├── voice_profile.py      — profile manifest data model
  ├── voice_approval.py     — approval gates (7.0/10 threshold)
  ├── voice_inventory.py    — asset inventory
  ├── voice_benchmark.py    — similarity benchmarking
  ├── cache_metadata.py     — WAV sidecar metadata
  ├── cache_advice.py       — cache repair suggestions
  ├── session_scorecard.py  — reliability report builder
  ├── safety_soak.py        — aggregate scorecard gate
  ├── rehearsal.py          — pre-call dry-run artifact
  ├── remediation.py        — fix suggestions from failures
  ├── regression_replay.py  — regression metrics from trigger samples
  ├── meeting_memory.py     — full-session transcript memory
  ├── trigger_capture.py    — trigger sample recording
  ├── trigger_sessions.py   — trigger sample ledger
  ├── provider_audio_readiness.py — BlackHole routing per provider
  ├── provider_latency.py   — provider latency measurement
  ├── f5_timing_metrics.py  — F5 pause timing analysis
  ├── f5_timing_review.py   — F5 timing review UI data
  ├── answer_cockpit.py     — Q&A cockpit UI data
  └── diarization.py        — optional speaker diarization check

speech/  (LLM composition — no TTS/audio deps)
  ├── composer.py           — Anthropic Claude standup composer
  └── ollama_composer.py    — Ollama composer (expand, classify, Q&A, standup)

tts/  (text-to-speech engines)
  ├── base.py               — TTSEngine protocol (synthesize, stop)
  ├── factory.py            — dispatch by engine name (6 engines)
  ├── selector.py           — purpose-specific engine resolution
  ├── naturalness.py        — NATURAL_PRESET, split_for_tts, breath samples
  ├── text_normalizer.py    — abbreviation expansion, number formatting
  ├── coqui_clone.py        — XTTS v2 zero-shot + fine-tuned
  ├── xtts_rvc.py           — XTTS + RVC v2 two-stage pipeline
  ├── f5tts.py              — F5-TTS one-stage (Russian-optimized, subprocess)
  ├── qwen3_tts.py          — Qwen3-TTS via MLX (Apple Silicon GPU)
  ├── piper_tts.py          — Piper TTS (CPU-friendly)
  ├── macos_say.py          — macOS `say` command (ultimate fallback)
  ├── trainer.py            — XTTS v2 fine-tuning
  ├── qwen3_trainer.py      — Qwen3 LoRA fine-tuning
  ├── dataset.py            — training dataset builder
  ├── prompts.py            — recording prompt texts
  ├── f5_presets.py         — named F5 pause timing presets
  ├── f5_corpus.py          — F5 preview test corpus
  └── quality.py            — A/B quality evaluator

audio/  (audio I/O — standalone, no saymo deps except self)
  ├── devices.py            — AudioDevice dataclass, device queries via sounddevice
  ├── capture.py            — AudioCapture (overlapping sliding-window, BlackHole)
  ├── playback.py           — play_audio_bytes, play_pcm, stop_playback
  ├── multi_play.py         — simultaneous multi-device playback
  ├── mic_processor.py      — gain, noise gate, highpass, spectral denoise
  ├── recorder.py           — record_voice_sample
  └── autocalibrate.py      — find optimal MicProcessor settings

providers/  (call platform automation — AppleScript, not CDP)
  ├── base.py              — CallProvider protocol, MeetingStatus
  ├── factory.py            — dispatch by provider name (8 providers)
  ├── _chrome_base.py       — Chrome-focused AppleScript automation
  ├── glip.py              — RingCentral Video (Space key)
  ├── zoom.py               — Zoom (Space key)
  ├── mts_link.py           — MTS Link (Space key)
  ├── telemost.py           — Yandex Telemost (Space key)
  ├── vk_teams.py           — VK Teams (Space key)
  ├── google_meet.py        — Google Meet (Space key)
  ├── ms_teams.py           — MS Teams (Space key)
  └── telegram.py           — Telegram Desktop (Space key)

plugins/  (data sources — auto-discovered by pkgutil.iter_modules)
  ├── base.py               — SourcePlugin protocol, discover_plugins()
  ├── obsidian.py           — Obsidian vault daily notes
  ├── confluence.py         — JIRA tasks (individual)
  ├── confluence_team.py    — JIRA tasks (team scrum)
  ├── jira_simple.py        — JIRA simple JQL
  └── file_summary.py       — plain-text file

stt/  (peech-to-text — standalone)
  └── whiper_local.py      — faster-whisper wrapper (LocalWhisper class)

utils/  (cross-cutting utilities)
  └── logger.py             — RichHandler logging, rich_tracebacks=True

config.py  (visited by nearly every module)
  └── SaymoConfig (nested dataclasses), load_config(), _resolve_env_vars()
```

### Key Dependency Rules

| Rule | Enforcement |
|------|------------|
| `audio/` imports nothing outside itself | Pure audio I/O |
| `t/` imports only `congi/audio.devices/analysis.voice_profile` | TTS depends on config, devices, profiles |
| `speech/` imports only `congi/jira_source` | Composition has no audio or tts deps |
| `providers/` imports only `providers._chrome_base/glip_control` | Provider abstraction is clean |
| `plugins/` imports only `plugins.base/jira_source/obsidian` | Plugin system is open for extension |
| `analysis/` imports everything including `commands` (lazy) | Central hub — a known coupling point |
| `commands/` imports every module | Top-level integration — expected |

## 3. Data Flow: Auto-Mode End-to-End

### 3.1 Startup Sequence

```
saymo auto --profile=personal
  │
  ├── 1. CLI dispatch (commands/core.py:391)
  │     resolve config, meeting profile, live tuning
  │
  ├── 2. Launch gate (core.py:471)
  │     evaluate_realtime_launch_gate()
  │     └── collect_launch_readiness() — 15 checks:
  │           provider tab, devices, cache, voice, daemon
  │
  ├── 3. Create core objects (core.py:566)
  │     ├── AudioCapture (16kHz, 4s chunks, 50% overlap)
  │     ├── LocalWhisper (large-v3, CPU int8)
  │     ├── TurnDetector (fuzzy name matching, 45s cooldown)  │     ├── ResonseCache (0 pre-synthesized intents)
  │     └── CallProvider (Glip/Zoom/etc.)
  │
  ├── 4. Hotkey listener (core.py:788)
  │     pynput.GlobalHotKeys → event flags + live-control
  │
  └── 5. Launch 3 concurrent asyncio tasks (core.py:1295)
        ├── _transcribe_loop()    - capture → STT → trigger
        ├── _trigger_loop()       - addressing → policy → playback
        └── _control_command_loop() - poll command queue
```

### 3.2 Transcription Loop

```
_transcribe_loop (core.py:837)
  │
  ├── while True:
  │     ├── if speaking/paused → sleep 0.5s
  │     ├── capture.get_chunk(timeout=3s) → np.ndarray (16000Hz, float32)
  │     ├── silence filter: RMS < 0.001 → skip
  │     ├── asyncio.to_thread(whisper.transcribe, chunk) → text
  │     └── TurnDetector.check(text):
  │           ├── regex match on name variants + fuzzy expansions
  │           ├── check cooldown (45s since last trigger)
  │           ├── search current chunk + prev+current concatenation
  │           └── on match → triggered.set()
```

### 3.3 Trigger → Response → Playback

```
_trigger_loop (core.py:895)
  │
  ├── await triggered.wait()  →  triggered.clear()
  │
  ├── 1. Handbrake check (realtime_gate.py:65)
  │     └── automatic_handbrake_block():
  │           ├── manual_takeover? → BLOCK
  │           ├── hard_disabled? → BLOCK
  │           └── auto_answer_enabled? → BLOCK if False
  │
  ├── 2. Addressing classification (addressing.py:101)
  │     └── classify_addressing(transcript, trigger_phrases):
  │           ├── 13-pattern cascade (handoff → question → mention)
  │           ├── returns AddressingDecision(label, confidence, is_question)
  │           └── should_answer_decision() → bool
  │
  ├── 3. Confidence confirmation (core.py:984)
  │     └── if require_confirmation:
  │           ├── first trigger → pending, wait 6s
  │           └── second trigger within window → confirmed
  │
  ├── 4. Live assist classifier (core.py:1013) — optional
  │     └── classifier can only DOWNGRADE (answer → skip)
  │
  ├── 5. Response resolution (realtime_policy.py:11)
  │     └── resolve_realtime_response_decision():
  │           ├── 1. ResponseCache.lookup(transcript)
  │           │     └── keyword match → score >= 0.6 → cached audio
  │           ├── 2. Cache miss + live_fallback → Ollama + TTS
  │           └── 3. Both fail → prepared standup audio
  │
  ├── 6. Pre-speak delay (default 2.0s)
  │
  ├── 7. Second handbrake + provider check (core.py:1106)
  │     └── provider_playback_block() → Chrome tab still open?
  │
  └── 8. Playback (core.py:1181)
        ├── speaking.set()  →  pauses transcription
        ├── asyncio.create_task(_play_cached_audio):
        │     └── provider.unmute_speak_mute(audio_callback):
        │           ├── get_previous_app
        │           ├── activate_meeting()  (focus Chrome tab)
        │           ├── toggle_mute()        (unmute via Space)
        │           ├── sleep 0.5s
        │           ├── asyncio.to_thread(sd.play + sd.wait)
        │           ├── activate_meeting()   (refocus)
        │           ├── toggle_mute()        (re-mute)
        │           └── restore_previous_app
        ├── concurrent stop_waiter (keyboard interrupt)
        ├── asyncio.wait(play_task, stop_waiter) with max_speech_duration timeout
        └── speaking.clear()
            cooldown reset
            "Listening again..."
```

### 3.4 Control Command Flow

```
Hotkey press (pynput daemon thread)
  │
  ├── loop.call_soon_threadsafe(_apply_control_action)
  │     └── append_control_command("toggle_auto_answer", "hotkey")
  │           └── writes JSONL to commands.jsonl
  │
  Control Daemon process (saemo call-control-daemon)
  │
  ├── pynput.GlobalHotKeys (same bindings)
  ├── queue_daemon_hotkey_command()
  │
  Auto process (_control_command_loop)
  │
  ├── polls commands.jsonl from last offset
  ├── processes: set event flags, write state.json
  └── append_control_audit() → audit.jsonl
```

## 4. Component Deep-Dives

### 4.1 Audio Pipeline

**Capture path:**

```
BlackHole 16ch → AudioCapture (InputStream callback, 4096 block)
  → [MicProcessor chain: highpass → denoise → gain → noise gate]
  → sliding window (4s chunks, 50% overlap)
  → queue.Queue (maxsize=30, ~120s buffer)
  → _transcribe_loop dequeues → RMS silence filter → whisper → text
```

**Playback path:**

```
TTS engine → WAV bytes → play_audio_bytes()
  → sd.play(np.ndarray @ 24000Hz, blocking=True)
  → asyncio.to_thread() → thread blocked on sd.wait()
  → (optional) play_bytes_to_devices() for monitor + BlackHole
```

**Key constants:**

| Parameter | Default | Location |
|-----------|---------|----------|
| Capture sample rate | 16000 Hz | core.py:568 |
| Chunk size | `chunk_seconds × sr` = 64000 | live.chunk_seconds (4.0) |
| Step size (overlap) | 32000 (50%) | live.hunk_seconds - live.overlap_seconds (2.0) |
| Silence RMS threshold | 0.001 | live.silence_rms_threshold |
| Playback sample rate | 24000 Hz | playack.py:19 |
| Stream block size | 4096 | capture.py:90 |

### 4.2 TTS Engine Layer

**Protocol (`tts/base.py`):**

```python
class TTSEngine(Protocol):
    async def syntheize(self, text: str) -> bytes: ...
    async def stop(self) -> None: ...
```

**Engine selection (`tts/selector.py`):**

Each purpose (preview, prepare, response_cache, realtime, live_call) has its own `VoiceSelectorPurposeConfig` with engine, fallbacks, voice profile, and `require_approved_profile` flag. `live_call` requires an approved profile by default.

**Dispatch (`tts/factory.py:49-82`):**

```
engine_name → class constructor

"coqui_cone"   → CoquiCloneTTS(language)
"xtts_rvc_clone" → XttsRvcCloneTTS(language, rvc)
"f5tts_clone   → F5TTSCloneTTs(langage, f5tts)
"qwen3_clon"   → Qwen3CloneTTS(language, model, lora_adapter)
"iper"          → PiperTTS(model_path)
"macos_say"     → MacOSSay(config)
```

**Synthesis approaches:**

| Engine | Model Loading | Inference Method | Output |
|--------|--------------|-----------------|--------|
| CoquiCloneTTS | Class-level LRU cache | Thread (`tto_thread`) | 24kHz WAV
| XttsRvcCloneTTS | CoquiCloneTTS + RVC suprocess | 2-stage thread | WAV
| F5TTSCloneTTS | Subprocess CLI call | Chunked natural pacing | 24kHz WAV (concatenated) |
| Qwen3CloneTTS | Class-level cache by (model, lora) | Thread via mlx_audio | WAV |
| PiperTTS | Thread (Piper Python API) | PCM
| MacOSSay | suprocess (`/usr/bin/say`) | WAV via stdin/AIFF

**Naturalness layer (`tts/naturalness.py`):**

```
NATURAL_PRESET = {
    "speed": 1.0,
    "temperature": 0.7,
    "repetition_penalty": 1.5,
}
```

`split_for_tts(text)` → splits into sentences, adds inter-sentence silece + optional breath pauses. Used by F5TTSCloneTTS.

### 4.3 Provider Automation Layer

```
BaseProvider (providers/ase.py)
  └─ MeetingStatuss (app_running, meeting_found, tab_info, mic_is_correct)
  └── check_ready() → MeetingStatus
  └── activate_meeting() → bool
  └── toggle_mute() → None
  └── switch_mic(device_name) → bool

ChromeBaseProvider (providers/_hrome_base.py)
  └── AppleScript-based Chrome control
      ├── name, url_pattern, mute_key, mute_modifiers
      ├── unmute_speak_mute(speak_fn):
      │     ├── get_previous_app()
      │     ├── activate_meeting() (AppleScript: tell Chrome to focus tab)
      │     ├── toggl_mute() (keystrok Space)
      │     ├── sleep(0.5)
      │     ├── speak_fn()  (play audio callback)
      │     ├── slep(0.3)
      │     ├── activate_meeting() (refocus to re-mute correctly)
      │     ├── toggl_mute()
      │     └── restore_previous_app()
      └── toggle_mute():
            └── tell app "Google Chrome" to activate
                tell app "System Events" to keystroke mute_key

Per-provider subclasses (8 total):
  ├── GlipProvider     (url: "v.ringcentral.com/conf")
  ├── ZomProvider      (url: "zoom.us")
  ├── MtsLinkProvider  (url: "mts-link.ru")
  ├── TelemostProvider (url: "telemost.yandex.ru")
  ├── VKTeamsProvider  (url: "teams.vk.com")
  ├── GoogleMeetProvider (url: "meet.google.com")
  ├── MSTeamsProvider   (url: "teams.microsoft.com")
  └── TelegramProvider (url: "web.telegram.org")
```

**Nore:** All providers use **AppleScript** for Chrome automation, not Chrome DevTools Protocol (CDP) despite the `_chrome_base` name. The CDP path was considered but not implemented.

### 4.4 Analysis Layer (Turn Detection)

**Turn Detector (`analysis/turn_detector.py`):**

```python
class TurnDetector:
    _patterns: list[re.Pattern]          # regex per name variant + fuzzy expansion
    _prev_text: str                       # previous chunk for span boundary detection
    _text_buffer: list[str]               # sliding window of last 20 chunks
    _last_trigger_time: float             # cooldown timestamp
    cooldown_seconds: float = 45.0

    def check(self, text: str) -> bool:
        # 1. cooldown check
        # 2. search current chunk
        # 3. search prev_chunk + " " + text (span boundary)
        # 4. on match → _last_trigger_time = time.time()
```

**Addressing Classifier (`analysis/addressing.py`):**

13-pattern cascade evaluated in order:
1. Floor handoff: `"слово {trigger}"`
2. Custom handoff (config)
3. Custom mention-only (config)
4. Third-person: `"что {trigger} думает"`
5. Collaboration: `"работали с {trigger}"`
6. Narrated: `"{trigger} говорил"`
7. Direct handoff: `"{trigger}, что"`
8. Team trigger + question
9. Bare trigger call
10. Plain mention (verb context)
11. Full-name mention
12. Default mention (no question)
13. Default question

Returns `AddressingDecision(label, confidence, is_question)`. Decision tree: `should_answer_decision()` → `True` for `addressed_to_me` or `generic_team_question`. `False` for `ignore`, `no_trigger`, `mentioned_not_addressed`.

**Response Cache (`analysis/response_cache.py`):**

- 20 default intents (all Russian): `status_generic`, `blockers_none`, `eta_today`, `help_needed`, etc.
- Each entry: `triggers` (keyword list), `variants` (answer texts), `description`
- Cache files: `~/.saymo/audio_cache/responses/{key}_{idx}_{text_sha1[:8]}.wav`
- Matching: tokenize transcript, compute ratio of trigger tokens present, compare to `confidence_threshold` (default 0.6)
- Stale detection: metadata file tracks voice profile hash → regeneration on voice change

**XML Classifier (`analysis/trigger_classifier.py`):**

- Naive Bayes with Laplace smoothing
- Features: transcript tokens + addressing/trigger metadata
- Trained on captured trigger samples (`trigger_sessions.py`)
- Live-assist mode: only downgrades (answer → skip), never force-speaks
- Readiness gating: >=10 labeled samples, >=3 accepted, >=3 rejected, >=2 categories

### 4.5 Plugin System

```python
class SourcePlugin(Protocol):
    name: str
    description: str
    async def fetch(self, config) -> dict | None:
        # Returns {"yesterday": str, "today": str, "yesterday_date": str, "today_date": str}

def discover_plugins() -> dict[str, type]:
    # Uses pkgutil.iter_modules on saymo/plugins/
    # Skips _ and base modules
    # Finds classes with both `name` and `fetch` attributes
```

| Plugin | Source | Data Type |
|--------|--------|-----------|
| Obsidian | `.md` files in vault | Daily notes |
| Confluence | JIRA JQL | Tasks (individual) |
| Confluence Team | JIRA JQL | Tasks (team rollup) |
| JIRA Simple | JIRA JQL | Simple assigned tasks |
| File Summary | `~/.saymo/summary.md` | Plain text |

Plugin output is injected into LLM prompt templates as `{yesterday_notes}` and `{today_notes}`.

## 5. IPC & Process Model

### 5.1 Process Architecture

```
┌─────────────────────────────────────────────────────────┐
│ macOS Processes                                            │
│                                                            │
│  ┌───────────────────────────────────────────┐            │
│  │ saymo auto  (Python, foreground)          │            │
│  │   ├── asyncio event loop                   │            │
│  │   ├── audio capture callback thread        │            │
│  │   ├── stt thread pool (whisper)            │            │
│  │   ├── tts thread pool (synthesis)          │            │
│  │   └── pynput GlobalHotKeys thread         │            │
│  └─────────────────────────────────────────────┘            │
│                                                            │
│  ┌───────────────────────────────────────────┐            │
│  │ saymo call-control-daemon  (Python, bg)    │            │
│  │   ├── pynput GlobalHotKeys thread          │            │
│  │   ├── heartbeat writer (2s)               │            │
│  │   └── polls commands.jsonl                 │            │
│  └───────────────┬───────────────────────────┘            │
│                  │ JSON file protocol                      │
│                  ▼                                          │
│  ~/.saymo/live_control/<profile>/                          │
│    ├── commands.jsonl     (written by any, read by auto)    │
│    ├── state.json         (written by auto, read by any)    │
│    ├── audit.jsonl        (written by auto)                 │
│    └── daemon-heartbeat   (written by daemon)               │
│                                                            │
│  ┌───────────────────────────────────────────┐            │
│  │ saymo live-control  (Python, foreground)   │            │
│  │   └── rich TUI reading state.json          │            │
│  └───────────────────────────────────────────┘            │
│                                                            │
│  External processes:                                       │
│    ├── Ollama (HTTP REST, localhost:11434)                 ││    ├── Chrome (AppleScript automation)                    ││    ├── ffplay / afplay (for macOS say)                   ││    └── Applio RVC (subprocess, separate venv)             ││                                                            │
│  LaunchAgents:                                             │
│    └── com.saymo.call-control.<profile>                    │
│          → saymo call-control-daemon --profile=<profile>   │
└────────────────────────────────────────────────────────────┘
```

### 5.2 Thread Model

| Thread/Coroutine | Purpose | Blocking? |
|-----------------|---------|-----------|
| Main asyncio loop | Event dispatch, hotkey callback | No |
| `_transcribe_loop` (coro) | Capture → STT → trigger detection | No (awaits) |
| `_trigger_loop` (coro) | Response resolution → playback | No (awaits) |
| `_control_command_loop` (coro) | Poll command queue | No (awaits) |
| Audio InputStream callback | Fill audio buffer from BlackHole | C-level, non-blocking |
| STT thread pool | faster-whisper inference | Yes (CPU-bound) |
| TTS thread pool | Model inference + file I/O | Yes (CPU-bound) |
| pynput GlobalHotKeys | OS-level key listener | Yes (thread) |

### 5.3 JSON File Protocol

All IPC between processes uses JSON files in `~/.saymo/live_control/<profile>/`:

**State (`state.json`):**
```json
{
  "profile": "standup",
  "auto_answer_enabled": true,
  "paused": false,
  "speaking": false,
  "manual_takeover": false,
  "hard_disabled": false,
  "hotkeys_active": true,
  "last_trigger": "",
  "last_action": "speak via hotkey",
  "updated_at": "2026-08-21T17:00:00Z"
}
```

**Command queue (`commands.jsonl`):**
```json
{"action": "speak", "source": "hotkey", "created_at": "...", "command_id": "abc123", "payload": {}}
```
Incremental reads via file offset tracking.

**Heartbeat (`daemon-heartbeat.json`):**
```json
{"profile": "standup", "pid": 12345, "heartbeat_at": "...", "hotkeys_active": true, "bindings_count": 9}
```
Written every 2 seconds by the daemon.

**Audit (`audit.jsonl`):**
```json
{"action": "speak", "source": "hotkey", "previous_state": {...}, "next_state": {...}, "result": "success", ...}
```

## 6. Config & State Management

### 6.1 Configuration Hierarchy

```
CLI flags (-c, -v)
  └── config.yaml  (user-writable, gitignored)
        ├── Env-var interpolation: ${VAR_NAME} in any string field
        ├── Meeting profiles (meetings.<name>) override base config per-call
        └── Prompt overrides (prompts.<key>) replace DEFAULT_* constants
```

Config loading (`config.py:load_config`):
1. Resolve path: CLI flag → default `~/.saymo/config.yaml` → `./config.yaml`
2. Parse YAML → nested dict
3. Recursive env-var resolution: `_resolve_dict()` on all string values
4. Map to `SaymoConfig` dataclass tree
5. Generate defaults for `blackhole_path` (auto-detect), `cache_dir`, `profile_dir`, etc.
6. Meeting profiles merged on top of base config

### 6.2 File System Layout

```
~/.saymo/
├── config.yaml
├── voice_samples/
│   └── voice_sample.wav
├── voice_profiles/<profile>/
│   └── profile.json
├── audio_cache/
│   ├── responses/
│   │   └── {key}_{idx}_{sha1[:8]}.wav
│   └── prepared/
│       └── {date}_{profile}.wav
├── training_dataset/
│   └── (raw WAVs + metadata.csv)
├── models/
│   ├── xtts_finetuned/
│   └── f5tts/
├── live_control/<profile>/
│   ├── state.json
│   ├── commands.jsonl
│   ├── audit.jsonl
│   ├── daemon-heartbeat.json
│   └── realtime-decisions.jsonl
├── trigger_samples/
│   └── (session records)
└── classifier/
    └── (trained model artifacts)
```

### 6.3 Profile System

Each `MeetingProfile` is a named overlay on base config:

```yaml
meetings:
  standup:
    description: "Daily team standup"
    provider: glip
    source: obsidian
    trigger_phrases: [Миша, Михаил]
    voice:
      engine: f5tts_clone
      profile: personal
    live:
      chunk_seconds: 3.0  # override base 4.0
```

Base config provides defaults; meeting profiles override specific fields.

## 7. Safety Architecture

### 7.1 Safety Layers (In Order of Application)

```
Layer 1: Launch Gate (evaluated once at startup)
  └── 15-point readiness checklist (launch_readiness.py:36-52)
        block: provider tab, capture device, playback device, BlackHole routing
        warn: cached audio state
        info: voice model metadata

Layer 2: Runtime Handbrake (evaluated per trigger)
  └── automatic_handbrake_block():
        manual_takeover? → BLOCK
        hard_disable? → BLOCK
        auto_nswer_enable? → BLOCK if False
         → ALOWED (all pass)

Layer 3: Addressing Classification (per trigger)
  └── 13-pattern regex cascade
        → addressed_to_me / generic_team_question / mentioned_not_addressed

Layer 4: Double-Trigger Confirmation
  └── 6s window for second name detection
        First trigger → pending, waitit
        Second withn 6s → confim

Layer 5: Live Assist Classifier (optional, shadow mode)
  └── ML classifier: can only downgrade (answer → skip)
      Cannot force-speak → safet boundar intact

Layer 6: Provider Check (right before playack)
  └── provider_check_ready() → BlOCK if meeting tab is gone

Layer 7: Max Speech Duration
  └── config.safety.max_speech_duration (default 120s)
      asyncio.wait(play_task, stop_waiter) with timeout

Layer 8: Hotkey Override (alway available)
  └── stop (Cmd+Sift+X), tdokeover (Cmd+Shift+U), hard_disable (Cmd+Shit+H)
```

### 7.2 Composition Logic

```
can_play = (launch_gate.passed)
         AND (automatic_handbrake_block() is Non)           # runtime
         AND (provider_playback_block() is Non)            # pre-playback
         AND (should_answer_decision() is True            # addressing
         AND (confirmation_pased OR notrquire_confirmation) # confirmation
```

### 7.3 Audi Logging

Every action, decision, and state change is logged to `audit.jsonl` with:
- Action name and source (hotkey, panel, cli)
- Previous and next state snapshots
- Result (success, block, skip, error)
- Reason for blocks/skips

## 8. Security & Privacy

### 8.1 Data Flow (Privacy)

```
User's voice sample
  │
  ├──→ Stored at ~/.saymo/voice_samples/ (local only)
  ├──→ Used for XTTS/RVC/F5/Qwen3 model training (local only)
  ├──→ Used for TTS synthesis (local inference)
  └──→ Never leaves the machine (default config)
        └── Optional: Anthropic Claude for composition (user opt-in)
```

### 8.2 Secrets Management

| Secret | Storage | Mechanism |
|--------|---------|-----------|
| JIRA token | config.yaml | `${JIRA_TOKEN}` → env var interpolation |
| Deepgram key | config.yaml | `${DEEPGRAM_KEY}` → env var interpolation |
| Anthropic key | config.yaml | `${ANTHROPIC_API_KEY}` → env var interpolation |
| Diarization token | env var | `os.environ.get("SAYMO_DIARIZATION_TOKEN")` |

### 8.3 Sanitization

- Launch readiness output: `_sanitize_text()` redacts `PRIVATE_*`, `SECRET_TOKEN`, `raw_transcript`, `audio_bytes`
- Realtime events: sanitized before writing to `realtime-decisions.jsonl`
- Cache metadata: stores only `text_sha256`, not the text itself
- Voice preview audit: stores only `text_sha256`, not the prompted text

### 8.4 macOS Permissions

| Permission | Required For | Setup |
|-----------|-------------|-------|
| Microphone | Capturing call audio via BlackHole | Granted during BlackHole install |
| Accessibility | Global hotkeys via pynput | `saymo hotkey-doctor` shows setup guide |
| Automation (Chrome) | Provider tab detection + mute/unmute | AppleScript via System Events |

## 9. Performance & Latency Budget

### 9.1 Latency Targets

```
Name detected (trigger_loop starts)
  │
  ├── (0ms)    AutomaticHandbrakeBlock check
  ├── (0ms)    Addressing classification (regex, CPU)
  ├── (0-6s)   Double-trigger confirmation window
  │
  ├── (0ms)   RealtimPolicy response resolution
  ├── (0-50ms)   ResonseCace lookup (tokenize + score, memory)
  ├── (0-5s)     Live fallback if cache miss (Ollama + TTS)
  │
  ├── (2.0s)     Pre-speak delay (cobutane)
  ├── (0ms)      Second handbrake + provider check
  │
  ├── (5-0ms)    Provider unmute (AppleScript keystroke)
  ├── (500ms)    Activation delay (sleeps)
  ├── (N sec)    Audio playack (speak duation)
  └── (500ms)    Provider e-mute + restoe app
```

| Scenario | Target | Contributors |
|----------|--------|--------------|
| Cache hit (confirmation off) | <500ms | Regex + tokenize + SDL load + play + provider automation |
| Cache hit (confirmation on) | <6.5s | Above + 6s confirmation window |
| Live fallback (confirmation off) | <5s | Above + Ollama compose (2-3s) + TTS synthesis (1-2s) |
| Cached standup cue (speak) | <1s | Audio fie load + provider unmute/speak/mute |

### 9.2 Performance Notes

| Bottleneck | Mitigation |
|------------|------------|
| STT (faster-whisper large-v3) | CPU int8 quantized; runs on thread; result is pipelined |
| TTS inference (XTTS / F5) | Runs on thread; F5 uses subprocess CLI |
| F5 chunked natural pacing | Subprocess per chunk → concatenated with silence |
| Provider automation | AppleScript + sleeps (300-500ms each); overall ~2s sequence |
| Model loading | Class-level LRU cache (Coqui, Qwen3); loaded once per process |
| Config loading | Single-shot at startup; meeting profiles merged on access |

## 10. Deployment & Packaging

### 10.1 Build Pipeline

```
brew deps (BlackHole, ffmpeg, ...)  ← install.sh
  │
  ├── uv venv + uv sync
  ├── pip install TTS / RVC / mxl-audio (conditional)
  ├── download whisper models
  ├── download XTTS / F5 models
  └── Jira source install
```

### 10.2 Runtime Dependencies

| Dependency | Type | Size |
|-----------|------|------|
| Python 3.11+ | Runtime | — |
| BlackHole 16ch + 2ch | System (brew) | ~20MB |
| faster-whisper large-v3 | Python + model | ~3GB |
| XTTS v2 | Python + model | ~2GB |
| F5-TTS (venv) | Subprocess venv | ~5GB |
| Ollama (optional) | System (brew) | ~500MB + model |
| Chrome | System | — |

### 10.3 CX (smo process packaging

`saymo` is a console script entry point in `pyproject.toml`:```toml
[project.scritps]
saymo = "saymo.cli:main"
```

Installed by `uv pip install -e .` into the project venv. The `uv run saymo` approach is also supported.

LaunchAgents are created at runtime by `saymo call-control-agent install --profile=X`, writing plists to `~/Library/LaunchAgents/com.saymo.all-control.X.plist`.

## 11. Key Design Decisions & Trade-Offs

| Decision | Rationale | Trade-Off |
|----------|-----------|-----------|
| Single asyncio process | Simple IPC, no shared state issues, easy debugging | No crash isolation; one failure kills everything |
| File-based IPC (JSON) | Debuggable with standard Unix tools, no socket/pipe complexity | Slower than sockets; no built-in RPC|
| AppleScript for Chrome | Works without Chrome flags, no open debugging port needed | Slower than CDP, Brittle agains Chrome updates |
| pynut for hotkeys | Cro-platform (even though we're macOS-only), well-tested | Requires Accessibility permission |
| Lazy imorts throughout | Fast CLI start time | Slightly more complex code |
| `asycio.to_thread` for blocking work | Reises main loop while CPU-bound inference runs | GIL limits true parallelism; no process isolation for crashing models |
| YAML config + env vars | Easy for users, standard, pattern matches industry | No schema validation at YAML parse time (validated at dataclass construction) |
| Naive Bayess classifier (not neural) | Runs on CPU instantly, tiny model, privacy | Lower accuracy than neural approaches |
