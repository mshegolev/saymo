# UX Design: Saymo

## 1. Design Principles

1. **Voice-first, CLI-native** — The primary interaction is the user speaking on a call and Saymo responding in their cloned voice. Configuration, diagnostics, and control are CLI-native with optional TUI augmentation.
2. **Safety by default** — Every automated action has an undo/override path. The user never speaks unintentionally. Hotkeys and handbrake are always available.
3. **Privacy as architecture** — No cloud round-trips in the default path. Setup warns when enabling optional cloud features (Anthropic, Deepgram).
4. **Progressive disclosure** — A beginner completes `saymo setup` in 6 steps. An expert deep-dives into `voice-profile`, `f5-presets`, `safety-soak`. The CLI groups commands by capability layer.
5. **macOS integration** — LaunchAgent for persistent daemon, Accessibility permissions for hotkeys, BlackHole for virtual audio, `osascript` for volume control.

## 2. Interaction Model

### 2.1 Primary Loop

```
┌─────────────────────────────────────────────────────────────┐
│  Live Call                                                    │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────┐  │
│  │ AudioCapture  │───▶│ faster-whisper   │───▶│ Turn       │  │
│  │ (4s windows)  │    │ STT (large-v3)   │    │ Detection  │  │
│  └──────────────┘    └──────────────────┘    └─────┬──────┘  │
│                                                     │          │
│                                        ┌────────────▼──────┐   │
│                                        │ Addressing Class.  │   │
│                                        │ (regex + LLM)     │   │
│                                        └─────────┬─────────┘   │
│                                                  │              │
│                              ┌───────────────────▼────────────┐ │
│                              │ Response Resolution            │ │
│                              │ Cache hit? → play <.5s         │ │
│                              │ Cache miss? → Ollama+TTS <5s  │ │
│                              │ Both fail → generic fallback   │ │
│                              └───────────────────┬────────────┘ │
│                                                  │              │
│                              ┌───────────────────▼────────────┐ │
│                              │ Provider Automation            │ │
│                              │ Unmute → Play → Mute          │ │
│                              │ (Chrome CDP + BlackHole)       │ │
│                              └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Interaction States

| State | Description | Visual Cue | Hotkey Action |
|-------|-------------|------------|---------------|
| **Idle** | Listening, no trigger | Status: "Listening..." (green) | Toggle off → Paused |
| **Paused** | Not listening | Status: "Paused" (yellow) | Toggle on → Idle |
| **Triggered** | Name detected, confirming | Status: "Triggered" (bold) | Stop → Idle |
| **Speaking** | Playback active | Status: "Speaking..." (cyan) | Stop → Playback stopped |
| **Takeover** | Mic handed to user | Status: "Manual takeover" (red) | Takeover → Idle |
| **Hard Disabled** | Everything stopped | Status: "HARD DISABLED" (red blink) | Hard Disable → Idle |

## 3. CLI UX

### 3.1 Command Hierarchy

```
saymo
├── setup               # Interactive wizard (6 steps)
├── auto                # Live call listening loop
├── speak               # Manual standup speak
├── quick               # Brief notes → speak
├── prepare             # Pre-cache standup + response audio
├── rehearsal           # Pre-call dry run
├── dashboard           # TUI control panel
├── live-control        # Handbrake TUI for a running auto
├── live-control-action # Queue one action (headless)
├── call-control*       # Daemon management group
│   ├── action          # Queue action
│   ├── probe           # Check daemon reachability
│   └── agent           # LaunchAgent lifecycle
├── voice-profile*      # Voice manifest management
│   ├── init / show / check / approve / reject
├── voice-inventory     # List all voice assets
├── voice-preview       # Preview cloned voice
├── train-*             # Training pipeline
│   ├── train-prepare   # Record samples
│   ├── train-rebuild   # Rebuild dataset
│   ├── train-voice     # Fine-tune XTTS/Qwen3
│   ├── train-qwen3     # LoRA fine-tune
│   ├── train-eval      # A/B evaluation
│   └── train-status    # Dataset/model status
├── f5-presets*         # F5-TTS pause timing presets
├── test-*              # Diagnostics group
│   ├── test-devices    # Audio devices
│   ├── test-tts        # TTS phrase
│   ├── test-compose    # Compose only
│   ├── test-ollama     # Ollama health
│   └── ...
├── dry-run / dry-run-compare  # Pre-flight checks
├── call-ready          # Launch readiness check
├── session-scorecard   # Reliability report
├── safety-soak         # Aggregated safety gate
├── cache-status        # Cache analytics
├── hotkey-doctor       # Hotkey diagnostics
├── provider-latency    # Provider playback latency
└── mic-check           # Audio calibration
```

### 3.2 Command Grouping by User Activity

| Activity | Commands |
|----------|----------|
| **Setup** | `setup`, `record-voice`, `voice-profile init`, `voice-profile check`, `train-prepare`, `train-voice`, `voice-profile approve` |
| **Daily Use** | `prepare`, `auto`, `speak`, `quick`, `live-control`, `live-control-action` |
| **Diagnostics** | `test-devices`, `test-tts`, `test-compose`, `test-ollama`, `hotkey-doctor`, `mic-check` |
| **Quality** | `rehearsal`, `call-ready`, `dry-run`, `session-scorecard`, `safety-soak`, `train-eval` |
| **Management** | `voice-profile`, `voice-inventory`, `cache-status`, `f5-presets`, `call-control-agent` |

### 3.3 Help Conventions

Every command has a `--help` with:
- Description (one line)
- Options table (flag, type, default, description)
- Usage example (if non-trivial)

Top-level: `saymo --help` shows grouped command list.
```
Saymo — AI-powered standup automation for Chrome-based calls.

Usage: saymo [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --config FILE  Path to config.yaml
  -v, --verbose      Enable debug logging

Commands:
  Setup:
    setup          Interactive setup wizard
    record-voice   Record voice sample for cloning
    voice-profile  Manage voice profile manifests
    train-voice    Fine-tune voice model

  Daily Use:
    prepare        Pre-generate standup + cache
    auto           Listen to live call, auto-speak
    speak          Read notes, compose, speak
    dashboard      Interactive control panel

  Diagnostics:
    test-devices   List audio devices
    test-tts       Test TTS engine
    hotkey-doctor  Check global hotkeys
    ...
```

## 4. Interactive Setup Wizard

### 4.1 Flow

```
saymo setup
┌─────────────────────────────────────────────────────────────┐
│ Welcome to Saymo! Let's set up your AI voice assistant      │
│                                                             │
│ Step 1/6: Your Info                                         │
│   What's your name? [________]                              │
│   Name variants (comma-sep): [________]                     │
│   Language: [ru / en]                                       │
│                                                             │
│ Step 2/6: Audio Devices                                     │
│   ┌──────────────────────────────────────────────────┐     │
│   │ # │ Name                    │ Type     │ Ch │ SR │     │
│   │───┼─────────────────────────┼──────────┼────┼────│     │
│   │ 0 │ BlackHole 16ch          │ Capture  │ 16 │ 48k│     │
│   │ 1 │ BlackHole 2ch           │ Playback │ 2  │ 48k│     │
│   │ 2 │ MacBook Pro Microphone  │ Capture  │ 1  │ 48k│     │
│   │ 3 │ MacBook Pro Speakers    │ Playback │ 2  │ 48k│     │
│   └──────────────────────────────────────────────────┘     │
│   Recording mic (# or name): [2]                            │
│   Playback device [BlackHole 2ch]:                          │
│   Monitor device (headphones): [3]                          │
│                                                             │
│ Step 3/6: Voice Sample                                      │
│   ▶ Recording in progress — read the prompts below          │
│   ┌────────────────────────────────────────────────────┐   │
│   │ Текст 1/5     ████████░░░░  0:45 / 1:00           │   │
│   │                                                     │   │
│   │ Сегодня я расскажу о задачах своей команды...       │   │
│   └────────────────────────────────────────────────────┘   │
│                                                             │
│ Step 4/6: Meeting Profiles                                  │
│   Name: [standup]                                           │
│   Provider: [glip / zoom / ms_teams / ...]                  │
│   Task source: [obsidian / jira / confluence / file]        │
│   Trigger phrases (comma): [Миша, Михаил, Misha]            │
│                                                             │
│ Step 5/6: LLM (Ollama)                                      │
│   ✓ Ollama is running                                       │
│   Select model: [qwen2.5-coder:7b ▸ llama3.2:3b ...]       │
│                                                             │
│ Step 6/6: TTS Engine                                        │
│   [▸] f5tts_clone  ✓ installed  Recommended                │
│   [ ] xtts_rvc_clone  ✓ installed                          │
│   [ ] coqui_clone  ✗ missing — pip install coqui-tts      │
│   [ ] macos_say  ✓ always available   Fallback             │
│                                                             │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Summary                                                │  │
│ │ Name:     Миша                                         │  │
│ │ Language: ru                                           │  │
│ │ TTS:      f5tts_clone                                  │  │
│ │ Profile:  standup → glip:Миша, Михаил, Misha          │  │
│ │ Config:   ~/.saymo/config.yaml                         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│ Next: saymo record-voice --duration 300                     │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Validation & Error Recovery

| Step | Validation | Error Message |
|------|-----------|---------------|
| Name | Non-empty | "Name is required. Please enter your name." |
| Audio devices | Device exists | "Device 'X' not found. Try `saymo test-devices`" |
| Voice sample | >= 10s | "Sample too short ({n}s). Minimum 10s. Try `--duration 30`" |
| Meeting profile | Provider exists | "Provider 'X' not supported. Choose from: glip, zoom, ..." |
| Ollama (optional) | HTTP probe | "Ollama not found at port 11434. Start with `ollama serve`" |

## 5. TUI Dashboard

### 5.1 Main Dashboard (`saymo dashboard`)

```
┌─────────────────────────────────────────────────────────────┐
│  Saymo Control Panel                           Миша | ru    │
├─────────────────────────────────────────────────────────────┤
│  Provider    ▸ glip                                          │
│               zoom                                           │
│               ms_teams                                       │
│                                                             │
│  Device      ▸ BlackHole 2ch                                │
│               MacBook Pro Speakers                           │
│                                                             │
│  TTS Engine  ▸ coqui_clone  piper  macos_say               │
│                                                             │
│  Source      obsidian                                        │
│                                                             │
│  Status      Ready ✓                                         │
│                                                             │
│  Summary     Сегодня я работаю над задачей DATA-123...      │
│              (300 chars, dim)                                │
│                                                             │
│  ── Hotkeys ──────────────────────────────────────────────  │
│  p  Prepare           s  Speak          g  Provider Speak    │
│  c  Cycle Provider    d  Cycle Device   e  Cycle Engine      │
│  t  Test TTS          r  Re-compose     x  Stop              │
│  q  Quit                                                    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Handbrake TUI (`saymo live-control --profile standup`)

```
┌─────────────────────────────────────────────────────────────┐
│  Saymo Live Control Handbrake — standup                     │
├─────────────────────────────────────────────────────────────┤
│  State          Listening                                    │
│  Auto Answer    ON  (green)                                  │
│  Paused         no                                           │
│  Speaking       no                                           │
│  Takeover       no                                           │
│  Hard Disable   no                                           │
│  Hotkeys        active                                       │
│  Last Trigger   —                                            │
│  State file     ~/.saymo/live_control/standup/state.json    │
│                                                             │
│  ── Controls ──────────────────────────────────────────────  │
│  a  Toggle Auto Answer    s  Speak         d  Approved      │
│  x  Stop                  u  Takeover      k  Skip          │
│  c  Capture Marker        i  Status        h  Hard Disable  │
│                                                             │
│  q quit   Ctrl+C quit                                       │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Color Semantics

| Color | Meaning |
|-------|---------|
| **bold cyan** | Section headers, key labels |
| **bold green** | Active/selected, success, ready |
| **bold red** | Errors, blockers, failures |
| **red blink** | Hard disable, critical state |
| **bold yellow** | Warnings, ambiguous states |
| **yellow** | Warnings, paused states |
| **dim** | Metadata, file paths, secondary info |
| **cyan** | Operation in progress, hotkey labels |

## 6. Voice Profile UX

### 6.1 Lifecycle Flow

```
saymo record-voice
  → ~/.saymo/voice_samples/voice_sample.wav

saymo voice-profile init --profile=standup --voice-sample=... --engine=f5tts_clone
  → ~/.saymo/voice_profiles/standup/profile.json

saymo voice-profile check --profile=standup
  → status: ready / blocked (with blocker list)

saymo train-voice --engine=f5tts_clone
  → Fine-tune output → model artifacts

saymo voice-profile approve --profile=standup --similarity=8.5 --artifacts=9.0 --call-readiness=7.2
  → approved: similarity=8.5; artifacts=9.0; call_readiness=7.2
```

### 6.2 Profile Status Display

```
$ saymo voice-profile show --profile=standup

  approved for calls: yes

  Profile       │ standup
  Engine        │ f5tts_clone
  Language      │ ru
  Voice sample  │ ~/.saymo/voice_samples/voice_sample.wav  (sha256: a1b2c3d4e5f6)
  Duration      │ 300s @ 22050Hz
  Transcript    │ transcript.txt  (4100 chars)
  Benchmark     │ run_20260821_163732  (similarity: 8.5)
  Fallback      │ approved
```

### 6.3 Approval Gate

| Score | Requirement | Validation |
|-------|------------|------------|
| similarity | >= 7.0/10 | Blind A/B comparison |
| artifacts | >= 7.0/10 | Audio quality check |
| call_readiness | >= 7.0/10 | Provider + BlackHole pipeline check |

Override available with `--override-reason` flag. Rejection stores reason in fallback_policy.

## 7. Daemon & Background UX

### 7.1 Per-Profile LaunchAgent

```
$ saymo call-control-agent install --profile=standup
  → ~/Library/LaunchAgents/com.saymo.call-control.standup.plist
  → Started com.saymo.call-control.standup

$ saymo call-control-agent status --profile=standup
  com.saymo.call-control.standup: running (PID 12345)
  Heartbeat: 2s ago
  Hotkeys: active
```

### 7.2 File-Based Protocol

All inter-process communication uses JSON files in `~/.saymo/live_control/<profile>/`:

```
~/.saymo/live_control/standup/
├── state.json           # Live state (read by TUI)
├── commands.jsonl       # Command queue (written by CLI/TUI, consumed by daemon)
├── daemon-heartbeat.json # Daemon health (written by daemon)
└── audit.jsonl          # Action audit log
```

This avoids socket/pipe complexity and allows inspection and debugging with standard Unix tools.

### 7.3 State JSON Schema

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

## 8. Error Messages & Diagnostics

### 8.1 Common Error Patterns

```
$ saymo auto
  ✗ Error: No meeting tab found for provider 'glip'
    Hint: Open a Glip meeting in Chrome first, then retry.
    See `saymo call-ready --profile=standup` for full readiness check.

$ saymo test-tts
  ✗ Error: Model file not found: ~/.saymo/tts/xtts_v2/model.pth
    Hint: Run `saymo setup` to download required models, or use --engine=macos_say

$ saymo hotkey-doctor
  Hotkey Doctor — standup
  ✓ saymo process running (PID 12345)
  ✓ pynput registered 9 bindings
  ⚠ macOS Accessibility permission required
    Open System Settings → Privacy & Security → Accessibility → add Terminal
```

### 8.2 Diagnostic Commands

| Command | Output |
|---------|--------|
| `saymo test-devices` | Table of all audio devices with BlackHole detection |
| `saymo test-ollama` | Ollama status + model list |
| `saymo hotkey-doctor` | Hotkey registration + macOS permission check |
| `saymo call-ready` | Provider + source + audio readiness matrix |
| `saymo cache-status` | Cache hit/miss stats, entries per intent |
| `saymo session-scorecard` | Reliability report for a session |

## 9. Accessibility & Safety

### 9.1 macOS Permissions

| Permission | Required For | Setup |
|-----------|-------------|-------|
| Microphone | Capturing call audio via BlackHole | Granted during BlackHole install |
| Accessibility | Global hotkeys (pynput) | `saymo hotkey-doctor` shows how |
| Automation | Chrome CDP control | Chrome must have `--remote-debugging-port` |

### 9.2 Safety Mechanisms

| Mechanism | Description | Trigger |
|-----------|-------------|---------|
| Double-trigger | Name must be heard twice within 6s | Auto-mode |
| Handbrake | Hard-stop via hotkey or TUI | `Cmd+Shift+H` or handbrake panel |
| Max duration | Playback auto-stops after N seconds | Config `max_speech_duration` |
| Rehearsal mode | Dry-run before live call | `saymo rehearsal` |
| Session scorecard | Post-call reliability report | `saymo session-scorecard` |
| Safety soak | Aggregate scorecards vs baseline | `saymo safety-soak` |

### 9.3 Status Indicator

The daemon heartbeat file can be monitored by external tools (e.g., sketchybar, iStat menus):

```json
{
  "hotkeys_active": true,
  "heartbeat_at": "2026-08-21T17:00:02Z",
  "bindings_count": 9
}
```

## 10. Visual Design System

### 10.1 Terminal UI Components

| Component | Library | Usage |
|-----------|---------|-------|
| Console | `rich.Console` | Global output, supports markup |
| Live | `rich.Live` | Dashboard and handbrake TUI refresh |
| Panel | `rich.Panel` | Section framing, wizard steps, summaries |
| Table | `rich.Table` | Device listings, profile attributes, controls |
| Progress | `rich.Progress` | Training progress bars |
| Text | `rich.Text` | Hotkey help text |
| Rule | `rich.Rule` | Section separators in training output |
| Logging | `rich.logging.RichHandler` | Rich tracebacks on errors |

### 10.2 Layout Patterns

- **Dashboards**: Single Panel containing a key-value Table + hotkey legend
- **Wizard**: Sequential steps, each with prompt + inline validation
- **Tables**: `show_header=False`, `box=None` for status displays; `show_header=True` for control tables
- **Progress**: `SpinnerColumn + TextColumn + BarColumn + TimeRemainingColumn` during training
- **Blinks**: Simulated via `Live` update with alternating colors (terminals without blink support)

### 10.3 Training UX Pattern

```
$ saymo train-voice --epochs=50

  Voice Training — standup
  ┌────────────────────────────────────────────────────────┐
  │ Model:   f5tts_clone                                    │
  │ Dataset: ~/.saymo/training/standup/  (12 samples, 8m) │
  │ Epochs:  50 / 50                                        │
  │                                                         │
  │ ████████████████████████████████████░░░░░  85%         │
  │ ETA: 12m 34s                                            │
  │                                                         │
  │ Loss: 0.0342   Best: 0.0311   LR: 3.2e-5              │
  └────────────────────────────────────────────────────────┘

  ✓ Training complete (50 epochs, 45m 12s)
  ✓ Model saved: ~/.saymo/models/standup/f5tts/
  ▸ Next: saymo train-eval to compare quality
```

### 10.4 Error Pattern

```
  ✗ Error: {brief description}
    Reason: {root cause}
    Hint: {actionable next step}
    See: `saymo {diagnostic command}` for details
```

Critical errors:
```
  ┌────────────────────────────────────────────────────────┐
  │  ⚠  HARDWARE ISSUE                                     │
  │  BlackHole 2ch not found. Audio routing requires        │
  │  BlackHole virtual audio driver.                        │
  │                                                         │
  │  Fix: brew install blackhole-2ch blackhole-16ch        │
  └────────────────────────────────────────────────────────┘
```