# Voice Clone Shootout

This guide explains how to compare Saymo voice-cloning engines before changing the production `tts.engine`.

## Baseline

The current baseline is F5-TTS Russian:

- `tts.engine: f5tts_clone`
- `~/F5TTS/models/ru/F5TTS_v1_Base_v2/model_last.pt`
- `~/F5TTS/models/ru/F5TTS_v1_Base/vocab.txt`

Do not change production config until a challenger wins blind A/B.

## Reference Recordings

Keep these files:

- `~/.saymo/voice_samples/voice_sample.wav`
- `~/.saymo/voice_samples/voice_sample.txt`

For a serious benchmark, record two additional clean references:

- 15 seconds: normal standup voice
- 45-60 seconds: statement, question, list, mild emphasis

## Run F5 Baseline

```bash
uv run python scripts/voice_clone_benchmark.py --engine f5tts --f5-nfe-step 16
```

On CPU, start with a smaller smoke run before spending time on the full set:

```bash
uv run python scripts/voice_clone_benchmark.py --engine f5tts --limit 3 --f5-nfe-step 16
```

Useful local-only overrides:

- `--voice-sample ~/.saymo/voice_samples/voice_sample.0024.wav`
- `--ref-text-file ~/.saymo/voice_samples/voice_sample.txt`
- `--f5-device cpu`
- `--f5-speed 0.95`

The command prints a run directory under:

```text
~/.saymo/voice_benchmarks/
```

`manifest.json` and `blind-review.md` are updated after each successful clip, so a long CPU run keeps completed results even if you interrupt it. Open `blind-review.md`, listen to each WAV, and score the audio-only review categories:

- similarity
- naturalness
- Russian pronunciation
- artifacts

Read latency from the run's `manifest.json`; it is not recorded in `blind-review.md`.

## Promotion Gate

A challenger can replace F5 only if:

- it wins at least 7 of 10 blind A/B comparisons on similarity,
- it has no worse artifacts than F5,
- it is repeatable from documented commands,
- for live-call use, it supports sub-8-second end-to-end answers or a cached fallback.

## Candidate Order

1. F5-TTS Russian baseline.
2. Qwen3-TTS Base zero-shot.
3. CosyVoice 3 zero-shot.
4. GPT-SoVITS fine-tune only if zero-shot candidates fail.

Do not install the next candidate until the previous candidate has a report.
