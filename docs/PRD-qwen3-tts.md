# PRD: Qwen3-TTS 1.7B + LoRA as Saymo's primary voice engine

Owner: user · Status: draft · Parent: `docs/voice-identity.md` (Track A.3 / B.3)

## 1. Context

Saymo's current primary cloning engine is **XTTS v2** (`saymo/tts/coqui_clone.py`). It works, and the fine-tune pipeline is shipped — but it has three hard limits that block the goals in `docs/voice-identity.md`:

1. **CPU-only on Apple Silicon.** MPS hits the 65536-channel convolution limit; training and inference run on CPU. A 3-epoch fine-tune on the current dataset took ~63 min on M1 16 GB, and inference for 1–2 sentences is 6–8 s — past the 5–7 s total budget for real-time answers.
2. **No streaming.** XTTS v2 produces the full WAV before playback can start; the call hears a long silent pause.
3. **Abandoned upstream.** Coqui is archived; there is no bug-fix path if something breaks.

**Qwen3-TTS 1.7B (`Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`)** addresses all three: MLX GPU on Apple Silicon, streaming generation (~1.8 s time-to-first-audio), active development by Alibaba. MOS after LoRA is reported at ~4.5 versus ~4.2 for XTTS v2 fine-tuned. LoRA fine-tunes ~2–5 M params in 1–2 h on M1 GPU.

Reference work: `github.com/cheeweijie/qwen3-tts-lora-finetuning`, `github.com/kapi2800/qwen3-tts-apple-silicon`.

## 2. Goals

- **G1** LoRA fine-tuning of Qwen3-TTS runs to completion on the existing 320-segment dataset and produces weights Saymo can load.
- **G2** Fine-tuned Qwen3-TTS wins ≥ 7 / 10 blind A/B pairs against base Qwen3-TTS zero-shot on the user's voice.
- **G3** Real-time synthesis for 1–2 sentences finishes in ≤ 3 s (time to final audio) on M1 16 GB with MLX GPU.
- **G4** Streaming path yields first audio chunk in ≤ 2 s, enabling the 5–7 s end-to-end answer budget in `docs/voice-identity.md` §6.5.
- **G5** `tts.engine: qwen3_clone` and `tts.realtime_engine: qwen3_clone` work as config switches without further code changes.
- **G6** **Hard CPU-only fallback.** Saymo must install, start, synthesise (non-streaming), and play prepared audio on a machine with no functional Apple Silicon GPU / MLX backend. No code path may `raise` solely because MLX GPU is unavailable; real-time paths degrade to the cached-audio path, and inference falls back to the XTTS v2 engine. See §5.5 for the compatibility matrix.

## 3. Non-goals

- Integrating F5-TTS, Fish Speech, or RVC — tracked separately; not in this PRD.
- Retiring XTTS v2. It stays as a CPU fallback until G2 + G3 are met on a real call.
- Rewriting dataset capture — the existing `saymo/tts/dataset.py` and `saymo train-prepare` pipeline is reused unchanged.
- Voice sample re-recording. If MOS plateaus below target, that is escalated as a separate "clean dataset" PRD.

## 4. Current state

What is already in place (and should not be rebuilt):

| Piece | Location | Status |
|---|---|---|
| MLX-based cloning engine | `saymo/tts/qwen3_tts.py:25-138` — `Qwen3CloneTTS` | works for zero-shot; accepts optional `lora_adapter` path (line 42); `load_model(..., adapter_path=...)` wired at lines 66-71 |
| LoRA training scaffold | `saymo/tts/qwen3_trainer.py:45-339` — `Qwen3VoiceTrainer` | dataset validation, LoRA application (`nn.LoRALinear.from_linear()` at lines 266-288), training loop, checkpoint save, `training_log.json` all present |
| LoRA hyper-params | `qwen3_trainer.py:138-139` | rank=8, scale=0.3 (matches reference repo) |
| Dataset format converter | `qwen3_trainer.py:109-133` — `_prepare_training_data` | emits JSONL with `{"text": ..., "audio": ...}`, 90/10 train/eval split |
| Training dataset | `~/.saymo/training_dataset/` | 320 good segments, ~37 min, `ready: true` |
| Reference audio for zero-shot | `~/.saymo/voice_samples/voice_sample.wav` | 5 min, 22.05 kHz, mono |

What is broken or missing:

| Problem | Location | Impact |
|---|---|---|
| Loss function is placeholder | `qwen3_trainer.py:290-301` — comment explicitly states "This is a placeholder"; fallback `return mx.mean(output)` | **blocks G1**. Training appears to run but gradients are nonsense; resulting adapter does not improve similarity |
| No streaming synthesis | `qwen3_tts.py:79-111` — `_synthesize_sync` writes full WAV to tmp dir, then reads it | **blocks G4**. Docstring at line 31 claims "Streaming generation for real-time Q&A" but there is no streaming path |
| No CLI entry for Qwen3 training | `saymo/cli.py` has `train-voice` (XTTS) but no `train-voice-qwen3` (or engine flag) | users cannot invoke the trainer |
| No A/B eval plumbing for Qwen3 | `saymo/tts/quality.py` / `saymo train-eval` only compares XTTS base vs fine-tuned | G2 cannot be measured |
| No `tts.realtime_engine` routing | `cli.py` auto mode only consults `tts.engine` | G5 requires branching |

## 5. Proposed solution

Four work items, in order:

### 5.1 Implement the training loss (unblocks G1, G2)

Investigate the `forward()` signature of `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` as loaded by `mlx_audio.tts.utils.load_model`. Two likely options:

- **Option A — teacher-forced token cross-entropy.** The model is autoregressive over audio tokens at 12 Hz; pass text + reference audio as conditioning, teacher-force ground-truth audio tokens, take mean negative log-likelihood. This is what `mlx-lm`'s LoRA loop does for text models and what the cheeweijie reference repo uses.
- **Option B — mel reconstruction L1/L2.** If Option A is not exposed, compute mel spectrograms of ground truth and model output and take L1 distance. Slower, less clean gradients; use only if A is not accessible.

Replace `qwen3_trainer.py:290-301` with the chosen implementation. Keep the batched `loss_and_grad_fn` pattern at line 192.

Acceptance check: loss decreases monotonically (±noise) across 5 epochs on the existing dataset; final loss < initial loss by ≥ 20%.

### 5.2 Streaming synthesis (unblocks G3, G4)

Add a streaming method to `Qwen3CloneTTS` that yields audio chunks as they are generated:

```python
async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]: ...
```

Hook it into `mlx-audio`'s streaming generator (check `mlx_audio.tts.generate` for a `stream=True` or generator-based API; if absent, iterate at the token level and flush every N tokens ≈ 250–500 ms of audio).

Playback side: add a writer that feeds a `sounddevice.OutputStream` chunk-by-chunk and routes to BlackHole 2ch. Reuse device resolution from `saymo/audio/devices.py`.

Acceptance check: first audible chunk ≤ 2 s after `synthesize_stream` is called; full 2-sentence utterance ≤ 3 s.

### 5.3 CLI + config integration (unblocks G5)

- Add `saymo train-qwen3` subcommand in `saymo/commands/voice_train.py`, mirroring the existing `train-voice` but wiring `Qwen3VoiceTrainer`. Flags: `--epochs`, `--rank`, `--scale`, `--lr`.
- Extend `saymo train-eval` to take `--engine qwen3` and A/B against the adapter at `~/.saymo/models/qwen3_finetuned/best_adapter/`.
- Add `tts.realtime_engine` key to `SaymoConfig` (`saymo/config.py`) and `config.example.yaml`. Default: same as `tts.engine`.
- In `_auto()` (`saymo/commands/core.py::_auto`), when the Track B intent classifier returns `specific_question`, use the engine from `tts.realtime_engine` instead of `tts.engine`.
- Update `docs/voice-identity.md` §7 (Config shape) to mark these keys as implemented.

### 5.4 Validation gate (unblocks G2)

Train, then run A/B. Do not promote the adapter to `realtime_engine` unless ≥ 7 / 10 pairs prefer the fine-tune. If the gate fails, record the adapter as "rejected" and open a follow-up against dataset quality (§7, Risks).

### 5.5 CPU-only compatibility (unblocks G6)

**Context.** Apple Silicon GPU via MLX is fast (Qwen3-TTS LoRA trains in 1–2 h, inference hits real-time budgets), but it is not universally available: MLX can fail to install, weights can be missing, or the user may run on a non-Apple machine for testing. Saymo must degrade, not crash.

**Compatibility matrix.** What must work at each capability level:

| Capability | GPU (MLX) | CPU-only | Behaviour on CPU-only |
|---|---|---|---|
| Install & import | required | required | both must succeed; MLX imports guarded so missing MLX is a warn, not a crash |
| Prepared playback (`saymo speak`) | works | **must work** | uses XTTS v2 (already CPU-only) |
| Zero-shot cloning (`Qwen3CloneTTS.synthesize`) | ~2–3 s | slow (~30–60 s) | runs via MLX CPU backend **or** auto-falls back to XTTS v2 per config flag |
| Streaming synthesis | ≤ 2 s TTFB (M5) | **out of scope** — returns full audio as a single chunk (no streaming, no guarantee on latency) | documented; no exception |
| LoRA training (`saymo train-qwen3`) | 1–2 h | **not supported** — prints an actionable error ("MLX GPU not available; use `saymo train-voice` for XTTS v2 on CPU") and exits cleanly | no silent CPU training that would take 10–20 h |
| A/B evaluation (`saymo train-eval`) | works | works (pre-generated samples) | no GPU dependency in `quality.py` |
| Real-time Q&A path in `_auto()` | ≤ 8 s (M6) | **disabled** — classifier still runs (Ollama), but on `specific_question` the system falls back to cached playback and logs the downgrade | no stuck calls |

**Implementation rules.**

- Gate all MLX imports (`import mlx.core as mx`, `from mlx_audio...`) behind `try/except ImportError` at module load, expose a `HAS_MLX_GPU` flag, branch in the engine factory.
- Add a startup probe: on first TTS use, run `mx.default_device()` and log `Device: GPU` or `Device: CPU (MLX fallback)` so the user sees current mode.
- `config.yaml` key: `tts.require_gpu: bool` (default `false`) — when `true`, refuse to start if GPU is not available (for production machines where silent CPU fallback would be a footgun).
- `saymo train-qwen3` is the only hard-refuse path on CPU — training is not viable there and silently running for 15 h is worse than failing fast.
- Every PR must be testable on a CPU-only environment. CI / local runs without MLX GPU must pass the full non-training test suite.

## 6. Success criteria (measurable)

| # | Metric | Target | How verified |
|---|---|---|---|
| M1 | LoRA training runs to completion | 0 exceptions, `best_adapter/` + `training_log.json` written | `saymo train-qwen3 --epochs 5` |
| M2 | Loss decreases | final loss < 0.8 × initial loss | `training_log.json` |
| M3 | A/B similarity | fine-tuned wins ≥ 7/10 vs base Qwen3 zero-shot | `saymo train-eval --engine qwen3` |
| M4 | Full-synthesis latency | ≤ 3 s for 1–2 sentences | `time saymo test-tts "<1-2 sent>" -e qwen3_clone` |
| M5 | Streaming TTFB | first audio chunk ≤ 2 s | new `test-stream-latency` script, measured three times |
| M6 | End-to-end Q&A | spontaneous answer in call ≤ 8 s total | live dry run through Glip with `tts.realtime_engine: qwen3_clone` |
| M7 | Trainable params sane | 2–10 M params, < 2% of total | `training_log.json` `trainable_params` / `total_params` |
| M8 | CPU-only compatibility | Saymo installs, starts, synthesises (non-streaming), and plays prepared audio on a machine where MLX GPU is unavailable; real-time path degrades to cached playback without exceptions | run full suite minus training with `MLX_DISABLE_GPU=1` (or equivalent) |

## 7. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `mlx-audio` does not expose a forward() that returns a loss | Med | Blocks G1 | Fall back to Option B (mel L1); if that is also inaccessible, upstream a minimal patch to `mlx-audio` or pin to the cheeweijie fork |
| `mlx-audio` streaming API is missing or unstable | Med | Blocks G4 | Ship §5.2 with chunked non-streaming first (synthesise N-token segments sequentially) to hit M5 conservatively; upgrade to true streaming once upstream lands |
| Dataset quality caps MOS below 4.5 | High | Blocks G2 | Dataset is currently YouTube-sourced, not studio. If A/B fails, escalate "clean re-record" as a separate PRD per `docs/voice-identity.md` §A.1 |
| Apple MLX memory pressure on M1 16 GB | Low | Training OOM | LoRA keeps base frozen; trainable is ~2–5 M params. If it still OOMs, drop `batch_size` to 1 (already default) and/or reduce sequence length |
| `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` weights require HF login / licence acceptance | Low | Blocks G1 | Document the `huggingface-cli login` step in the PR that adds `train-qwen3` |
| Model accidentally over-fits user's YouTube noise profile | Med | Low-similarity artefacts | Keep `eval_segments` (35 of 355) held out; watch eval loss divergence from train loss |

## 8. Timeline (engineer-days, solo)

| Day | Work |
|---|---|
| 1 | §5.1 — inspect `mlx-audio` API, prototype Option A loss, verify gradient flow on a 10-sample subset |
| 2 | §5.1 — full training run on 320 segments; iterate until M2 passes |
| 3 | §5.2 — streaming synthesis; hit M4, M5 |
| 4 | §5.3 — CLI, config, `_auto()` routing |
| 5 | §5.4 — A/B eval; live dry run on a real call; promote or reject adapter |

Total: ~1 working week. Matches the "1–2 days loss fix + 1–2 h training + 1–2 days integration" estimate in `docs/voice-identity.md`.

## 9. Rollout plan

**Step 0 (hard precondition).** The **CPU-only MVP** from `docs/voice-identity.md` §Execution order steps 1–5 must ship and pass its 7 / 10 A/B gate on XTTS v2 fine-tuned with a clean re-recorded dataset **before** any Qwen3 code lands. If the CPU-only MVP fails the gate, the fault is dataset quality, not the engine — no amount of Qwen3 work will fix it. Do not proceed past step 0 while the XTTS v2 pass is red.

1. Land §5.1 + §5.2 behind `tts.engine: qwen3_clone` — opt-in, XTTS v2 stays default. CPU-only fallback from §5.5 must be in place on the same commit — Saymo must not regress on non-GPU machines.
2. After M3 passes on a GPU machine, flip `tts.realtime_engine: qwen3_clone` in personal config; run a real call. On CPU-only installs, the `_auto()` spontaneous-answer branch continues to use the Tier-A response cache from MVP step 4 — unchanged.
3. After a clean 2-week usage window (no stuck-mic incidents, no "that didn't sound like me" flags), flip the `tts.realtime_engine` default in `config.example.yaml`. **Do not** flip `tts.engine` — XTTS v2 remains the prepared-playback default because it ships a working CPU path.
4. Revisit deprecation of XTTS v2 only after Qwen3-TTS has a verified CPU inference path that meets the prepared-playback latency bar (non-streaming, < 15 s per sentence acceptable). Until then XTTS v2 stays — it is the CPU-only guarantee.

## 10. Open questions

1. Does `mlx_audio.tts.utils.load_model` return a model object that exposes token logits, or only generated audio? Drives §5.1 Option A vs B.
2. Is `mlx_audio.tts.generate.generate_audio` (used at `qwen3_tts.py:86`) streamable, or must we drop to a lower-level API?
3. Reference-audio length at inference: current code passes the full 5-min `voice_sample.wav`. Should we trim to 10–20 s at synthesis time to reduce conditioning cost? Measure in M4.
4. LoRA target modules: `_apply_lora` currently adapts every `nn.Linear` in the graph (`qwen3_trainer.py:272-282`). Reference repos restrict to attention Q/K/V/O — should we narrow? Defer until M2/M3 data shows whether over-parameterisation hurts.

## 11. References

- Parent doc: `docs/voice-identity.md` (Track A.3, B.3, B.5)
- Current engine: `saymo/tts/qwen3_tts.py`
- Current trainer scaffold: `saymo/tts/qwen3_trainer.py`
- LoRA reference: https://github.com/cheeweijie/qwen3-tts-lora-finetuning
- Apple Silicon notes: https://github.com/kapi2800/qwen3-tts-apple-silicon
- Model card: `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` on Hugging Face
- MLX audio framework: `mlx-audio` (used via `from mlx_audio.tts.utils import load_model`)
