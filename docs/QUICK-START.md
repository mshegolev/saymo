# Quick Start — Zero to Your Voice in a Zoom Call

One document to get Saymo running on a fresh Mac in ~30 minutes.

## 1. Prerequisites & Installation

**System requirements:** macOS 13+ (Apple Silicon), Homebrew, Google Chrome.

Install [uv](https://docs.astral.sh/uv/) if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then run the installer:

```bash
cd /path/to/saymo
./setup.sh
```

`setup.sh` is the master setup. It runs the core installer, offers the
recommended F5-TTS voice engine, optionally installs the RVC path, and then
starts the interactive config wizard.

- Creates a Python 3.12 virtualenv via `uv`
- Installs system dependencies (`ffmpeg`, `portaudio`)
- Installs **BlackHole 2ch** (virtual microphone)
- Checks **BlackHole 16ch** (audio capture) and tells you how to install it if missing
- Installs Saymo core, TTS (Coqui XTTS v2), and STT (faster-whisper)
- Installs and starts **Ollama** with the `qwen2.5-coder:7b` model (~4.4 GB download)
- Downloads the Piper fallback voice model (~60 MB)
- Enables Chrome JavaScript from Apple Events (needed for call automation)

If you need to re-run only the config wizard later:

```bash
source .venv/bin/activate
saymo setup
```

The wizard walks you through configuring your name, audio devices, TTS engine,
and meeting profiles. It creates `~/.saymo/config.yaml` with your settings.

## 2. Audio Routing Setup

Saymo sends synthesized audio into Zoom through a virtual microphone (BlackHole 2ch) and captures call audio for auto-mode through BlackHole 16ch.

### Create the Multi-Output Device

1. Open **Audio MIDI Setup** (Spotlight → "Audio MIDI Setup")
2. Click the **+** button at the bottom left → **Create Multi-Output Device**
3. Check these outputs in order:
   - **Your headphones** (e.g., "External Headphones") — check the **Master** column
   - **BlackHole 16ch** — check **Drift Correction**
4. Rename it to "Multi-Output Device" (right-click → rename)

This lets you hear call audio while Saymo simultaneously captures it for transcription.

### Configure Zoom

1. Open Zoom → **Settings** → **Audio**
2. Set **Microphone** to **BlackHole 2ch**
3. Set **Speaker** to **Multi-Output Device**

### Verify

```bash
saymo test-devices
```

You should see BlackHole 2ch and BlackHole 16ch listed as available devices. If either is missing, restart your Mac — BlackHole sometimes requires a reboot after installation.

## 3. Voice Cloning

Record a 5-minute voice sample for voice cloning:

```bash
saymo record-voice -d 300
```

The command uses your configured microphone (or the system default). It generates on-screen text via Ollama for you to read aloud — just speak naturally in your normal pace.

The recording is saved to `~/.saymo/voice_samples/voice_sample.wav` and used by the TTS engine to clone your voice. For best results:

- Keep the microphone ~20 cm from your mouth
- Use a quiet room with minimal background noise
- Speak in your normal conversational tone

After recording, test the cloned voice:

```bash
saymo test-tts "Good morning everyone, this is a voice test."
```

You should hear the synthesized audio through your headphones. If the voice doesn't sound like you, check that the recording is at least 10 seconds long with peak volume above 0.5 — run `saymo test-voice-sample` to verify.

**Optional next step:** For higher voice similarity, see [VOICE-TRAINING.md](VOICE-TRAINING.md) for fine-tuning with `saymo train-prepare` and `saymo train-voice`.

## 4. Usage — Prepare & Speak

This is the two-step workflow: prepare your speech before the meeting, then play it during the call.

### Prepare

```bash
saymo prepare -p personal
```

Replace `personal` with the meeting profile you created in `saymo setup`
(`standup`, `demo`, or any other name).

This does two things:
1. Pulls your notes from the configured source (Obsidian daily notes, JIRA tasks, or a file)
2. Sends them to Ollama to compose a concise spoken update, then synthesizes each sentence as audio in your cloned voice

The audio is cached at `~/.saymo/audio_cache/` so playback is instant.

### Review (optional)

```bash
saymo review
```

Plays each sentence one by one. Bad sentences can be regenerated with adjusted parameters.

### Speak

When it's your turn on the Zoom call:

```bash
saymo speak -p personal --provider zoom
```

Saymo plays the cached audio into BlackHole 2ch (Zoom's microphone), and the call participants hear your cloned voice delivering the update.

Other providers use the same flag: `--provider glip`, `--provider google_meet`,
`--provider ms_teams`, `--provider telegram`, `--provider telemost`,
`--provider vk_teams`, `--provider mts_link`.

## 5. Usage — Auto Mode

Auto mode listens to the live call and responds automatically when your name is called.

```bash
saymo auto -p personal
```

How it works:
1. Captures call audio from BlackHole 16ch
2. Transcribes it in real time with faster-whisper
3. Detects when someone says your name (configured via `user.name_variants` in config)
4. Plays the best matching pre-synthesized response; if `responses.live_fallback`
   is enabled, Saymo can generate a live Ollama + TTS answer on cache miss

### Testing without a call

Use the `--mic` flag to test trigger detection using your physical microphone:

```bash
saymo auto -p personal --mic
```

Say your name out loud — Saymo should detect it and respond.

### Configuring trigger detection

In `~/.saymo/config.yaml`:

```yaml
user:
  name: "Your Name"
  name_variants:
    - "Your Name"
    - "your nickname"
```

Add any short forms or nicknames colleagues use on calls. For STT errors, add fuzzy expansions:

```yaml
vocabulary:
  fuzzy_expansions:
    Your Name: ["Your Name", "alternative spelling", "nickname"]
```

Before a real call, run a deterministic dry-run:

```bash
saymo trigger-check -p personal --text "Your Name, what is the status?"
```

Or use your microphone:

```bash
saymo trigger-check -p personal --mic
saymo trigger-setup -p personal --heard "misheard name, what is the status?"
saymo trigger-learn -p personal --heard "misheard name"
```

The report shows whether the phrase triggers Saymo, whether the mention is
addressed to you, whether it looks like a question, and whether a cached
response is ready.
If Whisper consistently hears your name incorrectly, use `trigger-setup` to
paste the whole transcribed phrase. Saymo extracts the likely name variant,
saves that spelling into `vocabulary.fuzzy_expansions`, and verifies it
immediately.

## 6. Troubleshooting

### Voice doesn't sound like me

Check your voice sample quality:

```bash
saymo test-voice-sample
```

The recording needs to be at least 10 seconds long with peak amplitude above 0.5. If it's too quiet, re-record in a quieter environment or move closer to the microphone. `saymo record-voice` does not normalize audio — what you record is what TTS uses.

### No audio in Zoom call

1. Verify Zoom microphone is set to **BlackHole 2ch** (Zoom → Settings → Audio)
2. Verify Zoom speaker is set to **Multi-Output Device**
3. Run `saymo test-devices` and confirm both BlackHole devices are listed
4. Try a test: `saymo test-tts "test"` — you should hear audio in your headphones
5. If BlackHole devices are missing, restart your Mac

### Ollama not responding

```bash
# Check if Ollama is running
curl http://localhost:11434

# Start it
brew services start ollama
# or: ollama serve

# Verify the model is available
ollama list
# If missing:
ollama pull qwen2.5-coder:7b
```

### STT not detecting trigger (auto mode)

1. Check `user.name_variants` in config — all name forms should be listed
2. Run `saymo trigger-check -p personal --mic` and say your name — watch the transcript output
3. If the name appears in the transcript but isn't detected, add the exact transcribed form to `name_variants`
4. Check microphone input level — run `saymo mic-check` to calibrate

### I need to answer myself during auto mode

Run once to add the default hotkeys:

```bash
./scripts/add_hotkeys.py
saymo takeover-check -p personal
```

During `saymo auto`, press `Cmd+Shift+U` for manual takeover. Saymo stops any
current playback, pauses auto-mode, and tries to switch the call microphone to
`audio.recording_device`. Unmute yourself in the call, answer, then press
`Cmd+Shift+U` again to switch back to `BlackHole 2ch` and resume Saymo.

Automatic mic switching depends on the provider. It is implemented for `glip`
and `mts_link`; for Zoom/Meet/Teams, switch the microphone manually in the
meeting UI.

## What's Next

- [VOICE-TRAINING.md](VOICE-TRAINING.md) — fine-tune XTTS on 10+ minutes of your recordings for higher similarity
- [F5TTS-VOICE-CLONING.md](F5TTS-VOICE-CLONING.md) — alternative TTS engine with better Russian voice quality
- [OVERVIEW.md](OVERVIEW.md) — full architecture and design decisions
- [PLUGINS.md](PLUGINS.md) — connect JIRA, Confluence, or other task sources
