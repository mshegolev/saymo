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
saymo auto-preflight -p personal
```

Or use your microphone:

```bash
saymo trigger-check -p personal --mic
saymo trigger-setup -p personal --heard "misheard name, what is the status?"
saymo trigger-learn -p personal --heard "misheard name"
```

The report shows whether the phrase triggers Saymo, whether the mention is
addressed to you, whether it looks like a question, and whether a cached
response is ready. It also reports whether auto-mode would answer now, wait for
confirmation, or skip the phrase. `auto-preflight` checks the prepared standup
cache, input/output devices, provider tab, configured trigger phrases, response
cache coverage, fallback mode, and live tuning before you join the call.
If Whisper consistently hears your name incorrectly, use `trigger-setup` to
paste the whole transcribed phrase. Saymo extracts the likely name variant,
saves that spelling into `vocabulary.fuzzy_expansions`, and verifies it
immediately.

Tune live detection globally or per meeting profile:

```yaml
live:
  chunk_seconds: 4.0
  overlap_seconds: 2.0
  trigger_cooldown_seconds: 45.0
  silence_rms_threshold: 0.001

meetings:
  personal:
    live:
      chunk_seconds: 3.0
      overlap_seconds: 1.0
```

During `saymo auto`, Saymo prints catch latency split by capture, STT, trigger
match, addressing/action, and playback start time.

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

### Collect trigger training samples

Run this during a call to save short windows for later trigger tuning:

```bash
saymo trigger-capture -p personal --session daily-2026-05-20
```

It listens on `audio.capture_device` by default, so use the same BlackHole
input as `saymo auto`. For a local one-minute test through your real mic:

```bash
saymo trigger-capture -p personal --session mic-test --device "MacBook Pro Microphone" --duration 60
```

Samples are written to `~/.saymo/trigger_samples/<profile>/` and split into
`asked_to_speak`, `mentioned_me`, `question`, and `speech` folders.
`asked_to_speak` means the speaker handed the floor to you or asked you
directly; `mentioned_me` means your name was mentioned without asking you to
speak. Each WAV has a JSON file with the transcript, trigger flag, question
flag, addressing label, levels, and capture `session_id`. Session ledgers are
written to `~/.saymo/trigger_samples/<profile>/_sessions/`, and capture prints
a final summary when it stops.

Review and tune the saved windows locally:

```bash
saymo trigger-sessions list -p personal
saymo trigger-sessions summary -p personal --session daily-2026-05-20
saymo trigger-sessions diarize -p personal --session daily-2026-05-20
saymo trigger-sessions speakers -p personal --session daily-2026-05-20
saymo trigger-sessions map-speaker -p personal --session daily-2026-05-20 --speaker-id SPEAKER_00 --label me
saymo trigger-samples list -p personal --session daily-2026-05-20 --speaker other
saymo trigger-samples list -p personal --classifier-disagreement --model-dir ~/.saymo/models/trigger_classifier
saymo trigger-samples label ~/.saymo/trigger_samples/personal/question/<sample>.json --speaker other
saymo trigger-samples decision ~/.saymo/trigger_samples/personal/question/<sample>.json --decision rejected
saymo trigger-samples category ~/.saymo/trigger_samples/personal/question/<sample>.json --category mentioned_me
saymo trigger-samples review -p personal --session daily-2026-05-20
saymo trigger-samples replay ~/.saymo/trigger_samples/personal/asked_to_speak/<sample>.json
saymo trigger-eval -p personal
saymo trigger-eval -p personal --promote ~/.saymo/trigger_samples/personal/asked_to_speak/<sample>.json
saymo trigger-classifier train -p personal
saymo trigger-classifier readiness -p personal
saymo trigger-classifier evaluate -p personal
saymo trigger-classifier live-assist enable -p personal
saymo trigger-classifier live-assist status -p personal
saymo trigger-classifier inspect -p personal
saymo trigger-eval -p personal --classifier-shadow
saymo trigger-classifier delete -p personal --yes
saymo trigger-samples report -p personal -o ~/.saymo/trigger_samples/personal-report.md
saymo diarization-check
```

`trigger-eval` reports stored/current categories, misses, and false positives.
It also groups results by speaker label: `me`, `other`, or `unknown`. Use
`trigger-samples label` to correct who spoke in a saved window; old samples
without a label are treated as `unknown`. `--promote` extracts the heard name
variant from one sample, writes it to `vocabulary.fuzzy_expansions`, and
immediately re-runs the evaluation. Use `trigger-samples decision` to mark an
answer decision as `accepted` or `rejected`, then run `trigger-classifier train`
after you have enough labels. Classifier artifacts stay local under
`~/.saymo/models/trigger_classifier/`, and `--classifier-shadow` on
`trigger-eval` or `trigger-check` compares learned confidence without changing
what Saymo would do live. Use `trigger-classifier inspect` or `delete` to audit
or remove the artifact. The report intentionally omits raw audio and transcript
text.

`trigger-sessions list` shows one row per capture run with saved-sample counts,
skipped silence windows, and a basic readiness hint. `trigger-sessions summary`
prints category, speaker, and answer-decision counts for one meeting session.
Use `trigger-samples category` when the automatic bucket is wrong, and
`trigger-samples review` when you want to walk a filtered queue after a call.
`trigger-classifier readiness` and `evaluate` must look healthy before enabling
live assist, and `enable` requires an existing trained classifier artifact.
Saymo stores a fingerprint of that model and disables live assist if the model
is missing or changed. Live assist only uses transcript/speaker features and
can downgrade an already deterministic answer candidate to skip; it cannot
bypass trigger/addressing checks.

Optional diarization starts disabled. Add a `diarization:` section to
`config.yaml`, keep tokens in env vars such as `SAYMO_DIARIZATION_TOKEN`, then
run `saymo diarization-check` before using speaker-suggestion workflows. The
session diarization sidecar stores speaker suggestions separately from sample
metadata; manual `speaker` labels are not overwritten by `trigger-sessions
diarize` or `map-speaker`.

### Measure call provider latency

Run this inside an active Chrome call when you need to separate call-provider
delay from capture/STT/trigger delay:

```bash
saymo provider-latency -p personal --text "Your Name, what is the status?"
```

Without `--text`, the command records a short window from `audio.capture_device`
and transcribes it locally before probing the provider. The report includes
capture, transcription, trigger decision, provider unmute, playback start,
playback duration, and mute recovery. JSON and Markdown history are written to
`~/.saymo/provider_latency/<profile>/<provider>/`.

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
Press `Cmd+Shift+S` when you want Saymo to speak the prepared cached standup
immediately without waiting for trigger detection.

Automatic mic switching depends on the provider. It is implemented for `glip`
and `mts_link`; for Zoom/Meet/Teams, switch the microphone manually in the
meeting UI.

## What's Next

- [VOICE-TRAINING.md](VOICE-TRAINING.md) — fine-tune XTTS on 10+ minutes of your recordings for higher similarity
- [F5TTS-VOICE-CLONING.md](F5TTS-VOICE-CLONING.md) — alternative TTS engine with better Russian voice quality
- [OVERVIEW.md](OVERVIEW.md) — full architecture and design decisions
- [PLUGINS.md](PLUGINS.md) — connect JIRA, Confluence, or other task sources
