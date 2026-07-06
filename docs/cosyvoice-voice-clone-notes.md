# CosyVoice Voice Clone Notes

CosyVoice is a future challenger gate only. Do not install CosyVoice packages, download models, or add a benchmark adapter until a Qwen3 Base score report exists. CosyVoice must not be installed before that.

## Current Status

Blocked until a Qwen3 Base score report exists under `~/.saymo/voice_benchmarks/<run_id>/score-report.md` and shows that Qwen3 Base was blocked or did not beat F5.

## Gate

CosyVoice is tested only after the F5 baseline and Qwen3 Base challenger. It must run in an isolated environment and produce the same benchmark outputs: WAV files, `manifest.json`, and `score-report.md`.

No production config switch is allowed.

Adapter requirements, when the gate opens:

- no changes to production `tts.engine`,
- isolated dependency environment,
- same phrase set,
- same output manifest schema,
- same blind review process.

If CosyVoice does not beat F5, do not install more zero-shot engines in this pass. Move to the fine-tune track decision.
