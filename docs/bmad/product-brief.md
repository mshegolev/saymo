# Product Brief: Saymo

## Vision

A fully local AI voice assistant for macOS that speaks in the user's cloned voice on live calls — eliminating the cognitive load of routine verbal updates so engineering teams can stay focused on deep work.

## Goals

1. Automate standup / scrum verbal reports on live calls with <500ms latency (cached) or <5s (live-generated)
2. Deliver near-identical voice similarity (>8/10) vs. the user's natural voice via on-device voice cloning
3. Keep the entire pipeline on-device — no cloud APIs, no voice data leaving the machine
4. Integrate with the 8 most common call platforms (Glip, Zoom, Meet, Teams, Telegram, Yandex Telemost, VK Teams, MTS Link)
5. Provide multiple safety layers (double-trigger, handbrake, rehearsal mode) so the user never speaks unintentionally

## Target Audience

- **Software engineers** on engineering teams that run daily standups via video calls
- **Technical leads / Scrum Masters** who give repeated status updates in multiple meetings
- **Privacy-conscious professionals** who cannot or will not route their voice through cloud APIs
- **Russian-speaking teams** (primary language is Russian; English also supported)
- Developers already using Obsidian or Jira as their task tracker

## Key Features

| Feature | Description |
|---|---|
| **Voice Cloning** | Zero-shot (XTTS, ~5 min setup), fine-tuned (XTTS+RVC, ~2-3h), or one-stage (F5-TTS Russian, ~10 min) |
| **Auto-Mode** | Listens for name on call via local STT, classifies addressing, auto-speaks cached or generated answer |
| **Response Cache** | Pre-synthesized answers for common standup questions — sub-second reply on CPU |
| **Live Fallback** | On cache miss, generates answer via Ollama + TTS in <5s |
| **Data Sources** | Obsidian vault, Jira, plain-text notes — configurable per meeting profile |
| **Call Automation** | Chrome JS injection for 8 providers — mute/unmute, join/leave detection |
| | **Safety** | Double-trigger, handbrake, rehearsal mode, max speech duration, manual takeover hotkeys |
| **Hotkeys** | Cmd+Shift+S (speak), X (stop), M (toggle), U (manual take over) |
| **Audio Calibration** | `saymo mic-check` — room/mic tuning, noise gate, highpass filter, noise reduction |  | **(example)** |
## Success Criteria

1. Voice similarity >= 8/10 in blind A/B test (fine-tuned pipeline)
2. End-to-end latency <500ms for cached responses, <5s for live-generated
3. Zero cloud API calls in default configuration path
4. Zero false-positive auto-speech events per 100 call minutes (after double-trigger config)
5. First-time setup (wizard + voice cloning) completable in under 30 minutes |
## Out of Scope

- Mobile (iOS/Android) or Windows/Linux support (macOS Apple Silicon only)
- Real-time conversation (Q&A only — assistant responds when addressed)
- Emotion-aware or expressive TTS (neutral professional tone only)
- Multi-speaker diarization or meeting summarization  |
