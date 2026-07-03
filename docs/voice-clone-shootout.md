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
uv run python scripts/voice_clone_benchmark.py --engine f5tts
```

The command prints a run directory under:

```text
~/.saymo/voice_benchmarks/
```

Open `blind-review.md`, listen to each WAV, and score:

- similarity
- naturalness
- Russian pronunciation
- artifacts
- latency

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
