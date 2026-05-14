# PRD: Saymo Quick Start Guide

## Problem Statement
New users have no single entry point to get Saymo up and running. Installation, audio routing, voice cloning, and usage across two main modes (prepare+speak, auto) are scattered across README, CLAUDE.md, and inline comments. A concise Quick Start guide in English is needed.

## Objectives
- Provide a single `docs/QUICK-START.md` file that takes a new user from zero to a working Saymo setup on macOS with Zoom
- Cover installation, audio routing, voice cloning, both usage modes, and troubleshooting
- Keep it concise and actionable — a guide, not a reference manual

## Target Users
New users installing Saymo for the first time on macOS. No prior knowledge of BlackHole, Ollama, or voice cloning assumed.

## Requirements

### Functional Requirements
- **Section 1: Prerequisites & Installation**
  - List system requirements (macOS, Homebrew, Chrome)
  - Describe `./setup.sh` as the master setup and `./install.sh` as the core installer it runs
  - Describe what the core installer handles (Ollama, BlackHole 2ch, BlackHole 16ch check, uv/pip dependencies, Chrome JS permission)
  - Describe `saymo setup` interactive wizard and what it configures
- **Section 2: Audio Routing Setup**
  - Step-by-step Audio MIDI Setup configuration
  - Create Multi-Output Device (headphones + BlackHole 16ch)
  - Set BlackHole 2ch as virtual microphone for Zoom
  - Verify routing with `saymo test-devices`
- **Section 3: Voice Cloning**
  - Record voice sample: `saymo record-voice -d 300`
  - Explain what happens and expected quality
  - Mention fine-tuning options (train-prepare, train-voice) as optional next step
- **Section 4: Usage — Prepare & Speak**
  - `saymo prepare -p <profile>` — what it does (LLM generates text, TTS caches audio)
  - `saymo review` — review generated sentences
  - `saymo speak -p <profile> --provider zoom` — playback during Zoom call
- **Section 5: Usage — Auto Mode**
  - `saymo auto -p <profile>` — listen for name, auto-respond
  - How trigger detection works (name variants)
  - `--mic` flag for testing without a call
- **Section 6: Troubleshooting**
  - Voice doesn't sound like me (check voice_sample peak/duration)
  - No audio in Zoom call (BlackHole routing misconfigured)
  - Ollama not responding (service not running, model not pulled)
  - STT not detecting trigger (name variants config, microphone level)

### Non-Functional Requirements
- Written in English
- Single markdown file: `docs/QUICK-START.md`
- Concise — aim for under 300 lines
- No private data or project-specific names in examples
- Use generic profile names in examples (e.g., `personal`, `standup`, `demo`)

### Technical Constraints
- macOS only (BlackHole, Audio MIDI Setup)
- Zoom as the primary call provider in examples
- Local-first: guide should work without any cloud API keys

## Success Criteria
- A new user can follow the guide end-to-end and successfully play Saymo audio into a Zoom call within 30 minutes (excluding voice training time)
- No steps require reading other documentation files

## Out of Scope
- Other call providers (Glip, Teams, Meet, etc.) — mention existence only
- Advanced voice training (RVC, LoRA fine-tuning) — link to dedicated docs
- Cloud TTS/LLM providers (Anthropic, OpenAI, ElevenLabs)
- Developer/contributor workflow
- Dashboard TUI usage

## Risks and Assumptions
- **Assumption:** User has macOS 13+ and admin access for Homebrew
- **Assumption:** User has Chrome installed for Zoom web client automation
- **Risk:** Audio MIDI Setup UI may differ across macOS versions — use descriptive steps rather than pixel-precise instructions
- **Risk:** BlackHole installation may require system restart — note this explicitly

## Timeline
- Single deliverable, no phased rollout
- Estimated effort: 1 session to write and verify
