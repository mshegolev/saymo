# Changelog

All notable changes to Saymo are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- F5-TTS Russian voice cloning engine — alternative one-stage path to XTTS+RVC, uses `Misha24-10/F5-TTS_RUSSIAN` (`docs/F5TTS-VOICE-CLONING.md`, `scripts/install_f5tts.sh`, `saymo/tts/f5tts.py`, new `tts.engine: f5tts_clone`)
- Phase 2 voice cloning: RVC v2 on top of XTTS for 9-10/10 perceived similarity (`docs/RVC-VOICE-CLONING.md`)
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

[Unreleased]: https://github.com/mshegolev/saymo/compare/v0.10.3...HEAD
[0.10.3]: https://github.com/mshegolev/saymo/compare/v0.10.2...v0.10.3
[0.10.2]: https://github.com/mshegolev/saymo/compare/v0.10.1...v0.10.2
[0.10.1]: https://github.com/mshegolev/saymo/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/mshegolev/saymo/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/mshegolev/saymo/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/mshegolev/saymo/compare/v0.7.1...v0.8.0
[0.7.0]: https://github.com/mshegolev/saymo/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/mshegolev/saymo/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/mshegolev/saymo/releases/tag/v0.5.0
