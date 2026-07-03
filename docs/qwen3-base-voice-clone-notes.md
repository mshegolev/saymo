# Qwen3 Base Voice Clone Notes

Qwen3-TTS Base is the first challenger because it is the Qwen3 variant intended for rapid voice cloning from user audio. The benchmark starts with zero-shot generation only. LoRA training is out of scope until zero-shot output beats or nearly matches F5.

## Current Execution Notes

- Use `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, not the CustomVoice cache.
- Keep this as a benchmark-only zero-shot gate. Do not add LoRA training to this task.
- Do not switch production `tts.engine` or local Saymo runtime config.
- Do not install `qwen-tts` or download model files until the benchmark adapter dry-run passes.
- Real generation should use the official `qwen_tts.Qwen3TTSModel` voice-clone API with reference audio and transcript text, while the manifest records only transcript length.
