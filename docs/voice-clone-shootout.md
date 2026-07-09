# Voice Clone Shootout

This guide explains how to compare Saymo voice-cloning engines before changing the production `tts.engine`.

## Baseline

The current baseline is F5-TTS Russian:

- `tts.engine: f5tts_clone`
- `~/F5TTS/models/ru/F5TTS_v1_Base_v2/model_last.pt`
- `~/F5TTS/models/ru/F5TTS_v1_Base/vocab.txt`

Do not change production config until a challenger wins blind A/B.

## Tune F5 Pause Presets

F5 pause tuning is config-only. It does not retrain the model, rewrite voice
samples, or touch training datasets.

```bash
saymo f5-presets list
saymo f5-presets show calm
saymo f5-presets corpus list
saymo f5-presets preview calm \
  --corpus standup \
  --output-dir ~/.saymo/voice_benchmarks/f5-standup-preview \
  --dry-run
saymo f5-presets preview calm \
  --corpus-id standup-blocked \
  --output-dir ~/.saymo/voice_benchmarks/f5-standup-blocked-preview \
  --dry-run
saymo f5-presets review ~/.saymo/voice_benchmarks/f5-standup-blocked-preview \
  --preferred calm \
  --notes "better pauses"
saymo f5-presets apply calm --profile standup
```

For a one-off local preview, keep manual text explicit and do not reuse it as
the repeatable tuning baseline:

```bash
saymo f5-presets preview calm \
  --text "Короткий тестовый текст для прослушивания." \
  --output-dir ~/.saymo/voice_benchmarks/f5-calm-preview \
  --dry-run
```

Built-in presets:

| Preset | Sentence | Clause | Silent breath / paragraph | Interval |
|--------|----------|--------|----------------------------|----------|
| `approved` | 0.38s | 0.18s | 0.60s | 2 |
| `crisp` | 0.26s | 0.12s | 0.42s | 2 |
| `calm` | 0.44s | 0.22s | 0.68s | 2 |
| `deliberate` | 0.55s | 0.28s | 0.85s | 2 |

Preview artifacts live under `~/.saymo/voice_benchmarks/<run>/` and store
`text_sha256`, `text_chars`, timing snapshots, preset ids, artifact paths, and
safe corpus metadata: corpus entry id (`corpus_id`, stored as JSON
`corpus.id`), category, and label. They never store raw manual text, corpus
phrase text, private meeting transcripts, prompts, response text, voice
samples, training data, secrets, or raw audio. Applying a preset writes both
`tts.f5tts.pause_preset` and the concrete timing knobs, so prepared audio and
response-cache metadata get a new voice fingerprint.

## Reference Recordings

Keep these files:

- `~/.saymo/voice_samples/voice_sample.wav`
- `~/.saymo/voice_samples/voice_sample.txt`

For a serious benchmark, record two additional clean references:

- 15 seconds: normal standup voice
- 45-60 seconds: statement, question, list, mild emphasis

## Inventory and Voice Profile

Before benchmarking, inspect local voice state without changing it:

```bash
saymo voice-inventory
saymo voice-inventory --json-output ~/.saymo/voice_inventory.json
```

The inventory is read-only. It reports active engines, known local model paths,
reference samples, transcript sidecars, datasets, audio caches, and benchmark
runs. It must not delete files, rewrite samples, start training, install
packages, or download model weights.

Create a profile manifest that references existing local files:

```bash
saymo voice-profile init \
  --profile personal \
  --voice-sample ~/.saymo/voice_samples/voice_sample.wav \
  --ref-text-file ~/.saymo/voice_samples/voice_sample.txt \
  --engine f5tts_clone \
  --dry-run

saymo voice-profile init \
  --profile personal \
  --voice-sample ~/.saymo/voice_samples/voice_sample.wav \
  --ref-text-file ~/.saymo/voice_samples/voice_sample.txt \
  --engine f5tts_clone \
  --apply

saymo voice-profile show --profile personal
saymo voice-profile check --profile personal
```

The profile stores paths, hashes, audio metadata, transcript character count,
engine, language, and approval state. It references the WAV/TXT files; it does
not copy or modify them. New profiles start with `approved_for_calls=false` and
cannot be treated as call-ready until later benchmark approval gates pass.

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

The benchmark writes:

- `manifest.json` — generated clips, engine settings, expected clip count,
  run status, and latency.
- `blind-review.md` — randomized listening order.
- `review.json` — human-fillable scoring template.
- `score-report.md` — run status, score status, latency summary, and promotion
  readiness.

These artifacts are updated after each successful clip, so a long CPU run keeps
completed results even if you interrupt it. Open `blind-review.md`, listen to
each WAV, then fill scores in `review.json`:

- similarity
- naturalness
- Russian pronunciation
- artifacts
- call readiness

Re-run the benchmark command or future scoring command after filling
`review.json` to regenerate `score-report.md`. A complete unscored run is not
promotion-ready; `score-report.md` must say `score status: scored` and
`promotion ready: yes` before a baseline or challenger can be used for an
approval decision.

## Run Qwen3 Base Challenger

Start with the dry-run gate. This exercises the benchmark path without importing `qwen_tts`, installing packages, or downloading model files:

```bash
uv run python scripts/voice_clone_benchmark.py --engine qwen3_base --limit 1 --dry-run
```

After the dry-run passes and an F5 baseline has a completed and scored
`score-report.md`, install the official package into an isolated Python
environment, then run the real challenger with the exact transcript and
baseline report:

```bash
uv run python scripts/voice_clone_benchmark.py \
  --engine qwen3_base \
  --ref-text-file ~/.saymo/voice_samples/voice_sample.txt \
  --baseline-report ~/.saymo/voice_benchmarks/<f5-run>/score-report.md
```

Useful local-only overrides:

- `--voice-sample ~/.saymo/voice_samples/voice_sample.0024.wav`
- `--ref-text-file ~/.saymo/voice_samples/voice_sample.txt`
- `--baseline-report ~/.saymo/voice_benchmarks/<f5-run>/score-report.md`
- `--qwen-model Qwen/Qwen3-TTS-12Hz-1.7B-Base`
- `--qwen-device-map auto`
- `--qwen-dtype auto`

Real Qwen3 generation fails fast if no transcript is provided through
`--ref-text`, `--ref-text-file`, or a sidecar `.txt` next to the reference WAV.
It also fails fast until `--baseline-report` points at a completed and scored
F5 `score-report.md`. Dry-runs do not require Qwen packages, model files,
transcripts, or baseline reports.

The Qwen3 Base benchmark uses the official `qwen_tts` Base path and records
`benchmark_path: official_qwen_tts_base` plus
`runtime_engine: not_qwen3_clone` in settings. That benchmark does not prove the
existing Saymo `qwen3_clone` MLX runtime is call-ready.

For approved local installs in this environment, prefer an isolated runtime and
the internal Nexus3 PyPI mirror when public PyPI is slow. Keep the mirror URL in
local shell config or operator notes, not in package metadata:

```bash
UV_HTTP_TIMEOUT=120 UV_CONCURRENT_DOWNLOADS=1 \
  uv pip install \
  --index-url <internal-nexus3-pypi-simple-url> \
  qwen-tts
```

Do not hardcode this mirror in committed project config or package files, and
do not use PyPI mirrors for model weights. Model weights remain explicit
Hugging Face or ModelScope assets.

See [Qwen3 Base Voice Clone Notes](qwen3-base-voice-clone-notes.md) for the current gate decision.

## Call-ready Selector

Runtime synthesis now has a purpose-aware selector:

- `preview`
- `prepare`
- `response_cache`
- `realtime`
- `live_call`

`prepare`, `prepare-responses`, cache-miss `speak`, approved draft playback,
and auto live fallback route through selector checks before instantiating a TTS
backend. Existing handbrake, confirmation, provider mute, stop, takeover, and
max-duration gates stay outside the selector and still run in the same order.

Default live-call behavior is fail-closed:

- missing voice profile → `voice_profile_missing`
- changed/missing reference WAV → `voice_profile_blocked`
- unapproved profile → `voice_profile_unapproved`
- non-cloned engine such as Piper/macOS `say` → `engine_not_voice_clone`
- stale/missing cache sidecar → `voice_metadata_stale` or
  `voice_metadata_missing`

Generated WAV caches now get sidecars next to the audio:

```text
~/.saymo/audio_cache/2026-07-07.wav.meta.json
~/.saymo/audio_cache/responses/status_generic_0_<hash>.wav.meta.json
```

The sidecar stores selector metadata, selected engine, attempted fallback
chain, cloned/non-cloned state, profile id, approval flag, and reference
hashes. It does not store transcript text or generated answer text.

Example selector override:

```yaml
voice_selector:
  default_profile: personal
  live_call:
    engine: f5tts_clone
    fallbacks: []
    allow_non_cloned: false
    require_approved_profile: true
  realtime:
    engine: qwen3_clone
    fallbacks:
      - f5tts_clone
```

## Preview and Approval

Preview locally before approving a voice for calls:

```bash
saymo voice-preview \
  --profile personal \
  --text "Проверяю голос перед звонком." \
  --dry-run
```

Dry-run writes a preview-only audit JSON under the profile directory without
synthesizing. A real preview omits `--dry-run` and plays locally through the
configured preview route. Audit metadata stores only selector data and a text
hash; it does not store preview text.

Approve a profile only after a completed/scored benchmark report:

```bash
saymo voice-profile approve \
  --profile personal \
  --score-report ~/.saymo/voice_benchmarks/<run>/score-report.md \
  --similarity 8 \
  --artifacts 8 \
  --call-readiness 8 \
  --apply
```

The approval gate requires:

- completed and scored `score-report.md`,
- `promotion ready: yes`,
- similarity >= 7,
- artifacts >= 7,
- call-readiness >= 7.

If you intentionally accept a lower score, pass `--override-reason` so the
profile records the exception. Rejecting clears call approval:

```bash
saymo voice-profile reject \
  --profile personal \
  --score-report ~/.saymo/voice_benchmarks/<run>/score-report.md \
  --reason "metallic artifacts in short answers" \
  --apply
```

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

Do not install the next candidate until the previous candidate has a completed
score report that justifies opening the next gate.

Next gates:

- [Qwen3 Base Voice Clone Notes](qwen3-base-voice-clone-notes.md)
- [CosyVoice Voice Clone Notes](cosyvoice-voice-clone-notes.md)
- [Voice Clone Fine-Tune Decision](voice-clone-finetune-decision.md)
