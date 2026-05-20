# Changelog

All notable changes to Saymo are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `saymo trigger-capture` captures live call-audio windows into
  `~/.saymo/trigger_samples/<profile>/` as WAV plus JSON metadata, classified
  into `asked_to_speak`, `mentioned_me`, `question`, `speech`, and optional
  `silence` samples for trigger-training review.
- Named trigger-capture session ledgers with `trigger-sessions list` and
  `trigger-sessions summary`.
- `trigger-samples category`, `trigger-samples review`, and session-aware
  sanitized reports for correcting sample category, speaker, and answer labels
  without manually editing JSON.
- `trigger-classifier readiness`, deterministic holdout `evaluate`, and
  guarded `live-assist status|enable|disable` commands.
- `trigger-check --live-assist` diagnostics for local classifier confidence,
  model state, and final guarded action.

### Changed
- Local trigger classifier behavior can now be promoted from shadow diagnostics
  to guarded live assist after readiness passes and a trained model fingerprint
  matches the current artifact.
- Public examples and docs now use generic ACME / John-style placeholders
  instead of project-, company-, or person-specific names.

## [0.12.0] — 2026-04-30

### Added
- **`saymo/tts/naturalness.py`** — single source of truth for XTTS prosody presets and helpers used by every TTS-generation script in the repo. Exports `NATURAL_PRESET`, `CONSERVATIVE_PRESET`, `ENERGETIC_PRESET`, `resolve_voice_sample(language)` (per-language reference fallback), `load_breath_sample()` (extracts a real inhale from the user's voice sample to splice between paragraphs instead of digital silence), `split_for_tts(text)` (sentence/paragraph/`[pause:N]`-aware splitter), and shared inter-segment pause constants.
- **`docs/VOICE-NATURALNESS.md`** — consolidated rulebook (reference recording specs, source-text rules, XTTS parameter cheat-sheet, fine-tuning, WER-based quality verification via Whisper). Distilled from ElevenLabs, Inworld AI, and Coqui XTTS-v2 official guides plus internal experiments.
- **`scripts/synthesize_presentation.py`** — one-shot helper that synthesizes presentation text in the user's cloned voice. Uses the shared naturalness module, supports `--preset natural|conservative|energetic`, `--language`, and `[pause:N]` markers.
- **`scripts/play_to_glip.py`** — standalone "press button → talk to Glip" runner: stashes the currently-selected Glip mic, switches to BlackHole 2ch, plays a WAV via the existing provider unmute → speak → mute flow, then restores the original mic. Includes a global stop hotkey (`Cmd+Shift+X` by default), `Ctrl+C` handler that re-mutes Glip and restores the mic, and `--mic-back` override.
- **`get_current_rc_mic()`** in `saymo/glip_control.py` — reads the currently-selected microphone label from the Glip audio dropdown via Chrome JS injection; used by `play_to_glip.py` to remember the user's real mic across a playback.
- **XTTS prosody kwargs forwarding** in `saymo/tts/coqui_clone.py` — `CoquiCloneTTS.synthesize(text, **kwargs)` now passes `speed`, `temperature`, `repetition_penalty`, `length_penalty`, `top_k`, `top_p`, `enable_text_splitting` straight through to XTTS for both base and fine-tuned checkpoints.

### Changed
- **`switch_rc_mic_to_blackhole()` generalised to `switch_rc_mic_to(device_name)`** in `saymo/glip_control.py` — accepts any substring of a Glip mic-dropdown label (e.g. `"BlackHole 2ch"`, `"MacBook Pro Microphone"`, `"AirPods"`). Old function kept as a backwards-compatible wrapper.
- **`GlipProvider.switch_mic(device_name)`** now actually honours its `device_name` argument (previously hardcoded to BlackHole 2ch regardless).
- **`CLAUDE.md` + `AGENTS.md`** — added architectural rule that TTS-generation code must import presets/helpers from `saymo/tts/naturalness.py` rather than re-deriving constants per-script.

## [0.11.0] — 2026-04-24

### Added
- **`setup.sh`** — single-command master orchestrator. Walks user through Saymo core install → F5-TTS install → optional RVC install → wizard. Idempotent.
- **`docs/QUICK-START.md`** — single-page from-zero-to-working-voice walkthrough.
- **`docs/OVERVIEW.md`** — architecture overview, stack table, file layout, threat model summary.
- **F5-TTS Russian voice cloning engine** — alternative one-stage path to XTTS+RVC, uses `Misha24-10/F5-TTS_RUSSIAN` (`docs/F5TTS-VOICE-CLONING.md`, `scripts/install_f5tts.sh`, `saymo/tts/f5tts.py`, new `tts.engine: f5tts_clone` — now the recommended default).
- **Phase 2 voice cloning**: RVC v2 on top of XTTS for 9-10/10 perceived similarity (`docs/RVC-VOICE-CLONING.md`, `scripts/install_rvc.sh`, `scripts/train_rvc.sh`, `saymo/tts/xtts_rvc.py`, new `tts.engine: xtts_rvc_clone`). RVC training pipeline runs headlessly (preprocess → extract → train → index → install artifacts) and can be triggered automatically after `saymo train-voice`.
- Tunable RVC parameters via `tts.rvc.{protect,clean_audio,clean_strength}` (previously hardcoded — `protect=0.5` reduces metallic artifacts).
- Open-source community files: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, GitHub issue/PR templates, CI workflow (ruff + pytest on macOS-14), release workflow (auto GitHub Release from tag), Dependabot config, `.editorconfig`, `.gitattributes`.
- README badges (License/Python/Platform/CoC/PRs welcome) + voice-cloning quality tier table.
- Maintainer email in `pyproject.toml` for `SECURITY.md` / CoC reporting routes.

### Changed
- **Wizard now offers all 4 TTS engines** (`f5tts_clone`, `xtts_rvc_clone`, `coqui_clone`, `macos_say`), detects which are installed, and points the user at the right installer script for missing ones. No longer tries to install Coqui TTS inline (was using a deprecated `.venv-tts` path).
- README quick-install section now starts with `./setup.sh` instead of `./install.sh` directly. `install.sh` is still the base step `setup.sh` invokes.

### Fixed
- `train-eval` plays A/B audio to `monitor_device` (your headphones) instead of `playback_device` (the call-app virtual mic). Same bug class as commit `e3f9a8e` for `test-tts` and `wizard`.
- `coqui_clone.py` `isin_mps_friendly` compatibility patch (needed for `transformers >= 5.x` with Coqui TTS) is now applied before either model load branch, so `train-eval`'s base-model load no longer crashes.
- `scipy` moved from `[tts]` optional extra to core dependencies — used by `saymo.audio.mic_processor` highpass filter outside of TTS, was missing in CI.

### Removed
- Unused `openai` and `elevenlabs` engine config sections + dead `saymo/tts/openai_tts.py` module (factory tests already treated them as unknown).
- `scripts/install_rvc.sh` — idempotent installer for Applio (training) + rvc-python (inference)
- `scripts/train_rvc.sh` — headless RVC training pipeline (preprocess → extract → train → index → install artifacts)
- `saymo train-voice` now offers to launch RVC training as a follow-up step in interactive sessions
- Open-source community files: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, GitHub issue/PR templates
- Voice-quality tier table in `README.md`

### Fixed
- `train-eval` now plays A/B audio to `monitor_device` (your headphones) instead of `playback_device` (the call-app virtual mic). Same bug class as `e3f9a8e` for `test-tts` and `wizard`. (`saymo/tts/quality.py`)
- `coqui_clone.py` `isin_mps_friendly` compatibility patch is now applied before either model load branch, so `train-eval`'s base-model load no longer crashes on `transformers >= 5.x`. (`saymo/tts/coqui_clone.py`)

## [0.10.3] — 2026-04

### Fixed
- `test-tts` and `wizard` route through `monitor_device` instead of `playback_device`

## [0.10.2] — 2026-04

### Fixed
- `prepare` no longer hardcodes `speech.source = confluence`; respects user config

## [0.10.1] — 2026-04

### Fixed
- Clear error message when `jira.url` / `jira.token` are not configured (instead of crash)

## [0.10.0] — 2026-04

### Added
- Various stability and config-handling improvements
- Re-routed wizard through monitor device

## [0.9.0] — 2026-03

### Added
- Auto mode latency logging, safety hotkeys, playback timeout, TTS warmup
- LLM intent classifier before `ResponseCache` keyword match
- Q&A pipeline smoke-test harness

## [0.8.0] — 2026-02

### Added
- `train-qwen3` shortcut and LoRA hyperparameter flags
- `tts.realtime_engine` override for live auto-mode (split slow high-quality from fast realtime)
- CLI split into `saymo/commands/` submodules
- Unit tests for `TurnDetector` and `ollama_composer`

### Removed
- Glip-specific dead code from `glip_control`

## [0.7.0] — 2026-02

### Added
- Public-release prep: mic calibration, Tier-A response cache, Qwen3-TTS docs, PyPI metadata

### Fixed
- Real bugs surfaced by Pyright (0.7.1)

## [0.6.0] — 2026-01

### Added
- Qwen3-TTS engine with (experimental) LoRA fine-tuning support

## [0.5.0] — 2026-01

### Added
- Voice-training pipeline (XTTS v2 GPT-decoder fine-tune)
- `train-prepare`, `train-voice`, `train-eval`, `train-status` CLI

## Earlier

For commits before v0.5.0, see `git log --tags --simplify-by-decoration` — the project moved to formal versioning at v0.5.0.

[Unreleased]: https://github.com/acme/saymo/compare/v0.11.0...HEAD
[0.11.0]: https://github.com/acme/saymo/compare/v0.10.3...v0.11.0
[0.10.3]: https://github.com/acme/saymo/compare/v0.10.2...v0.10.3
[0.10.2]: https://github.com/acme/saymo/compare/v0.10.1...v0.10.2
[0.10.1]: https://github.com/acme/saymo/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/acme/saymo/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/acme/saymo/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/acme/saymo/compare/v0.7.1...v0.8.0
[0.7.0]: https://github.com/acme/saymo/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/acme/saymo/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/acme/saymo/releases/tag/v0.5.0
