# Research: v1.8 Call-ready Voice Clone Pitfalls

**Project:** Saymo
**Milestone:** v1.8 Call-ready Voice Clone
**Researched:** 2026-07-07
**Confidence:** HIGH for repo-specific gates and current implementation risks; MEDIUM for future engine-specific API behavior until real packages are installed and tested.

## Summary

The main way this milestone can fail is by treating "a generated voice clip exists" as enough evidence for live-call readiness. Saymo already has a strong safety contract from v1.5-v1.7: generated drafts must be explicitly approved, runtime handbrake state must be respected, and safety-soak must catch regressions before real calls. v1.8 must extend that contract to voice identity, model assets, benchmark evidence, and fallback behavior.

The safest phase order is: first inventory and profile local voice assets read-only, then establish a reproducible F5 baseline, then test challengers behind strict dry-run/download gates, then wire a call-ready selector and fallback chain, and only then allow preview/A-B approval plus safety-soak promotion. Heavy downloads, training, CosyVoice experiments, and production config switches should be impossible before their evidence files exist.

Specific repo risks are visible in the current files. `scripts/voice_clone_benchmark.py` has good dry-run, manifest, and transcript-redaction behavior, but it does not produce the `score-report.md` that `docs/cosyvoice-voice-clone-notes.md` uses as the next-candidate gate. `saymo/tts/qwen3_tts.py` still advertises streaming but only writes a full WAV through `mlx_audio`, while the shootout docs require the official `qwen_tts.Qwen3TTSModel` Base API for Qwen3 zero-shot. `saymo/tts/qwen3_trainer.py` is safer than the old placeholder because unsupported loss shapes raise, but training remains out of scope unless a later fine-tune decision explicitly opens it.

## Pitfalls

| Pitfall | What Goes Wrong | Why It Derails v1.8 | Phase That Must Own It |
|---|---|---|---|
| Protected voice assets are treated like disposable cache | Broad cleanup or inventory code deletes, rewrites, moves, or re-transcribes `~/.saymo/voice_samples`, `~/.saymo/training_dataset`, `~/.saymo/models`, or `~/F5TTS` assets | Recreating checkpoints/datasets is expensive, and the user explicitly constrained this milestone to no destructive deletes and no unapproved training/downloads | Phase 31 - Voice Asset Inventory and Profile Setup |
| The project starts training or model downloads before gates | Qwen, CosyVoice, or fine-tune commands install packages/download weights/run training during discovery, docs tests, or dry-runs | Downloads and training are expensive, can require auth/license acceptance, and contaminate a benchmark that should be reproducible and user-approved | Phase 31 and Phase 33 |
| Benchmark evidence is incomplete or not comparable | F5, Qwen3, and future candidates use different phrase sets, reference WAVs, transcript text, device settings, or manifest schemas | A/B results cannot justify replacing `tts.engine`; a challenger can "win" because the run was easier, not because it is better | Phase 32 - Benchmark Harness and F5 Baseline |
| `score-report.md` is assumed to exist but the benchmark only writes manifest/review files | `docs/cosyvoice-voice-clone-notes.md` blocks CosyVoice until a Qwen3 score report exists, but `scripts/voice_clone_benchmark.py` currently writes `manifest.json` and `blind-review.md` only | The next-candidate gate becomes manual memory instead of a file-backed rule; CosyVoice can start too early | Phase 32 before any Phase 33 candidate expansion |
| Qwen3 Base shootout is confused with production `qwen3_clone` | The shootout docs require `Qwen/Qwen3-TTS-12Hz-1.7B-Base` via official `qwen_tts`, while `saymo/tts/qwen3_tts.py` uses `mlx_audio`, defaults to CustomVoice, has unused model-loading paths, and does not stream | A good Qwen3 Base benchmark would not prove the current runtime engine is call-ready; a runtime config switch could promote the wrong code path | Phase 33 - Candidate Shootout Gates; Phase 34 - Engine Selector |
| Qwen3 API shape handling silently degrades | Official Qwen returns bytes, file paths, dicts, object wrappers, `(sample_rate, audio)`, or `([audio], sample_rate)`; dtype/device options differ by package version | Prior work already saw dtype/tuple-shape risk. If result handling is wrong, benchmarks may save corrupt WAVs, report false latency, or crash after download | Phase 33 |
| Qwen3 LoRA/fine-tune work sneaks into the zero-shot milestone | Developers fix `qwen3_trainer.py`, run `train-qwen3`, or promote adapters while the milestone is still a benchmark shootout | Training is expensive and explicitly out of scope until zero-shot output beats or nearly matches F5; bad training evidence can waste days | Phase 33, with a separate future fine-tune phase only after a written decision |
| Reference transcript quality is ignored | F5 falls back to a generic Russian phrase; Qwen3 real generation is run without `--ref-text-file` or sidecar `.txt`; transcript content leaks into manifests/logs | Voice similarity and pronunciation degrade, and reference text may become private data in committed artifacts | Phase 31 and Phase 32 |
| Blind review is biased or non-repeatable | Review order changes without a fixed seed/run id, filenames reveal engines, reviewers see latency before scoring, or partial interrupted runs are treated as complete | The 7/10 promotion gate loses meaning; engine selection becomes subjective and unrepeatable | Phase 32 |
| Latency is measured too narrowly | Only per-clip synth time is recorded, while model setup, prompt creation, audio routing, playback timeout, and first-audio timing are ignored | A voice can sound good but miss the live-call budget. Current Qwen3 benchmark records setup latency, but call readiness needs route-aware timing too | Phase 32 and Phase 35 |
| Fallback chain changes the user's identity silently | `macos_say` or Piper fallback speaks into the call without making it clear that the output is not the user's cloned voice | This violates the product promise and can be worse than not speaking; fallback must be safe and explicit, not invisible | Phase 34 |
| Live runtime speaks cloned audio before approval | A config switch or new engine path bypasses `answer-cockpit`, preview, timeout, max-duration, handbrake, or safety-soak checks | This directly violates the v1.5-v1.7 safety boundary: unapproved generated text/audio must never reach the call | Phase 35 - Preview, A/B Approval, and Safety Soak |
| Preview routing hits the call output | Preview playback uses `BlackHole 2ch` instead of the monitor device, or the monitor fallback is not visible to the user | The user may think they are previewing while meeting participants hear unapproved cloned audio | Phase 35 |
| Optional dependency isolation is broken | F5-TTS packages, Qwen packages, CosyVoice packages, MLX, Torch, and Transformers are installed into one environment or imported at module load | Saymo's normal tests and fallback engines break on machines without heavy ML deps; local-by-default stops being lightweight | Phase 33 and Phase 34 |
| Engine selector bypasses the factory | New code imports `F5TTSCloneTTS` or `Qwen3CloneTTS` directly instead of using `get_tts_engine(config, realtime=...)` | `tts.realtime_engine`, fallback behavior, test seams, and optional import safety drift apart | Phase 34 |
| Naturalness rules are applied inconsistently | New scripts split text differently, tune parameters inline, skip loudness/route checks, or ignore reference sample language/style | Benchmark results overfit script quirks; call output can sound robotic even when the engine is good | Phase 32 and Phase 35 |
| Safety-soak remains blind to voice-clone readiness | Soak checks only trigger/playback state and does not know which engine, voice profile, benchmark approval, or fallback mode was used | v1.8 can pass old reliability gates while using an unapproved voice clone | Phase 35 |

## Prevention Strategy

### Phase 31 - Voice Asset Inventory and Profile Setup

Purpose: establish protected local state and a voice profile without changing assets.

Required gates:

- Inventory must be read-only by default. It may stat, hash, inspect metadata, and report paths, but must not delete, normalize, rewrite, transcribe, train, or download.
- The command output must clearly classify assets as `usable`, `missing`, `stale`, `duplicate`, `dangerous_to_delete`, or `requires_user_action`.
- Include local asset roots in docs and tests: `~/.saymo/voice_samples/`, `~/.saymo/training_dataset/`, `~/.saymo/models/`, `~/F5TTS/`.
- Voice profile setup must require explicit flags for any mutation, for example `--record`, `--write-profile`, `--transcribe-reference`, or future `--train`.
- Reference WAV checks should report duration, sample rate, channel count, sidecar transcript presence, and whether it matches `docs/VOICE-NATURALNESS.md` expectations.

Concrete tests/docs:

- Add unit tests that inventory uses temporary directories and does not mutate file mtimes or contents.
- Add a docs section in `docs/voice-clone-shootout.md` or a new voice-profile doc stating "inventory is read-only; training/downloads require explicit commands".
- Add regression coverage for transcript redaction: manifests may include transcript length, never transcript text.

### Phase 32 - Benchmark Harness and F5 Baseline

Purpose: make the current F5 baseline measurable before challengers are allowed.

Required gates:

- Keep `scripts/voice_clone_benchmark.py --engine f5tts --dry-run` and real F5 generation separate.
- Preserve benchmark phrase order and phrase ids across engines.
- Continue writing `manifest.json` after each successful clip so long CPU runs keep partial evidence.
- Add `score-report.md` generation from blind review scores and manifest latency. This file is the gate for Qwen3/CosyVoice phase decisions.
- Lock manifest schema for all engines: engine, phrase id, text prompt, output WAV, latency, setup latency if applicable, and settings with transcript length only.
- Score report must say whether the run is complete, partial, interrupted, or rejected.

Concrete tests/docs:

- Keep and extend `uv run pytest tests/scripts/test_voice_clone_benchmark.py`.
- Add tests that `score-report.md` is not produced as passing unless every selected phrase has a WAV and score entry.
- Update `docs/voice-clone-shootout.md` so "Promotion Gate" points to `score-report.md`, not informal notes.
- Add a command example for a fast CPU smoke run and full F5 run.

### Phase 33 - Candidate Shootout Gates

Purpose: test challengers without dependency sprawl or accidental promotion.

Required gates:

- Qwen3 Base real generation is blocked until F5 has a completed baseline score report.
- Qwen3 Base starts with `--dry-run`; dry-run must not import `qwen_tts`, install packages, or download weights.
- Real Qwen3 generation must require `--ref-text`, `--ref-text-file`, or sidecar `.txt`.
- Qwen3 Base must use `Qwen/Qwen3-TTS-12Hz-1.7B-Base` and official `qwen_tts.Qwen3TTSModel` for the shootout, not the current `saymo/tts/qwen3_tts.py` CustomVoice path.
- CosyVoice remains blocked until a Qwen3 Base `score-report.md` says Qwen3 was blocked or failed to beat F5.
- No LoRA training or adapter promotion in this phase. If zero-shot results justify fine-tuning, write a separate decision doc first.

Concrete tests/docs:

- Keep `test_generate_qwen3_base_dry_run_writes_manifest_without_importing_qwen`.
- Keep tuple/dict/file/bytes audio result tests for Qwen3 output handling.
- Add a test that real Qwen3 exits if reference transcript is missing.
- Add a test or doc gate that CosyVoice adapter cannot be invoked without an existing Qwen3 score report path.
- Document every install command as user-approved and out of dry-run flow.

### Phase 34 - Call-ready Engine Selector and Fallback Chain

Purpose: wire only proven engines into Saymo runtime without bypassing existing safety contracts.

Required gates:

- All runtime TTS selection goes through `saymo.tts.factory.get_tts_engine(config, realtime=...)`.
- `tts.engine` remains the prepare/default engine; `tts.realtime_engine` is an optional live-path override.
- Fallback chain must be explicit in config and audit output: cloned voice fallback and non-cloned fallback are different states.
- If a cloned engine fails or times out, live mode should prefer a prepared/cached approved response over unlabelled `macos_say` speech.
- Optional imports stay deferred. A machine without Qwen/Cosy/F5 packages must still import Saymo and run non-ML tests.
- `saymo/tts/qwen3_tts.py` must not be promoted as call-ready until its model path, adapter usage, and streaming claims match the shootout evidence.

Concrete tests/docs:

- Keep `uv run pytest tests/tts/test_factory.py`.
- Add tests for fallback order and audit metadata: selected engine, attempted engine, fallback engine, cloned vs non-cloned flag, blocked reason.
- Add a startup/preflight command that reports current engine, realtime override, dependency availability, reference sample, and last approved benchmark report.
- Update `config.example.yaml` comments so fallback engines are clearly marked "not the user's voice".

### Phase 35 - Preview, A/B Approval, and Safety Soak

Purpose: prove that approved cloned voice can be heard safely before real calls.

Required gates:

- Preview must default to monitor route when available and must clearly record `preview:true` in audit events.
- "Speak" must remain an `answer-cockpit` approved action; hotkey `approved_speak` may request it but must not bypass the cockpit path.
- A/B approval must require at least 7/10 blind wins, no worse artifacts than baseline, and a linked score report.
- Safety-soak must fail if a scorecard or audit implies unapproved draft playback, manual takeover active, hard-disable active, missing benchmark approval, unknown voice profile, or fallback to non-cloned voice without explicit consent.
- Latency checks must include synthesis timeout, route/playback completion, and for future streaming, first-audio timing.

Concrete tests/docs:

- Keep approved playback tests in `tests/test_trigger_check.py` and `tests/analysis/test_answer_cockpit.py`.
- Extend safety-soak tests (`tests/test_safety_soak_cli.py`, `tests/analysis/test_safety_soak.py`) with v1.8 voice readiness fields.
- Add a preview/A-B doc section that says "approval of text is not approval of voice profile"; both gates must pass before live call use.
- Add manual UAT: preview to monitor, preview with BlackHole disconnected, approved speak to BlackHole, timeout/stop hotkey, fallback blocked/labelled.

## Warning Signs

- A command named `inventory`, `doctor`, `benchmark --dry-run`, or `profile setup` imports Qwen/Cosy packages, downloads a model, modifies `~/.saymo`, or takes minutes instead of seconds.
- A benchmark run directory lacks `manifest.json`, `blind-review.md`, or `score-report.md`.
- `manifest.json` contains the full reference transcript instead of only `ref_text_chars`.
- `blind-review.md` exposes engine names in a way that biases scoring, or the review order changes after scoring starts.
- A challenger report uses fewer phrases than the F5 baseline without marking the run as partial.
- Qwen3 results come from `saymo/tts/qwen3_tts.py` while the report claims to evaluate Qwen3 Base official `qwen_tts`.
- `saymo/tts/qwen3_tts.py` is configured as `tts.realtime_engine` even though it still uses full-WAV generation and has no measured call-route latency.
- `train-qwen3` appears in the implementation plan before a zero-shot score report and fine-tune decision exist.
- Training logs show `total_steps == 0`, flat loss, missing `best_adapter`, or many swallowed step warnings.
- `config.example.yaml` changes the default `tts.engine` or `tts.realtime_engine` before a 7/10 A/B gate and safety-soak pass.
- A fallback voice speaks into a call without audit metadata saying it is not cloned voice.
- Preview output route is `BlackHole 2ch` when a monitor device was configured.
- Safety-soak output has no notion of voice profile, benchmark approval, selected engine, or fallback status.

## Phase Placement

| Phase | Recommended Name | Primary Risk Controls | Exit Criteria |
|---|---|---|---|
| 31 | Voice Asset Inventory and Profile Setup | Protected local assets, read-only discovery, reference transcript checks, voice-profile manifest | Inventory/profile commands report all local assets without mutation; tests prove no writes/deletes; docs state explicit mutation/training gates |
| 32 | Benchmark Harness and F5 Baseline | Comparable phrase set, manifest schema, score-report generation, transcript redaction, partial-run handling | F5 dry-run and smoke/full benchmark produce `manifest.json`, `blind-review.md`, and `score-report.md`; tests cover redaction and incremental output |
| 33 | Candidate Shootout Gates | Qwen3 dry-run first, official Qwen3 Base path, no CosyVoice before Qwen report, no fine-tune/training | Qwen3 Base can be dry-run without imports and real-run only with transcript; CosyVoice remains blocked unless Qwen score report permits it |
| 34 | Call-ready Engine Selector and Fallback Chain | Factory-only dispatch, `tts.realtime_engine`, explicit cloned/non-cloned fallback labels, optional dependency isolation | Engine selector reports selected/fallback engines; tests cover realtime override and fallback audit metadata; no package import regressions on normal test suite |
| 35 | Preview, A/B Approval, and Safety Soak | Monitor preview, explicit approval, 7/10 A/B gate, latency/timeout, safety-soak voice readiness | Preview/A-B flow links to score report; safety-soak fails missing approval/unapproved/fallback hazards; approved playback remains cockpit-gated |

Do not add a fine-tune phase inside v1.8 unless Phase 33 produces evidence that zero-shot is close enough to justify it and a separate decision doc accepts the training/download cost. If added later, that phase must own Qwen3 loss-shape validation, `MLX_DISABLE_GPU`/CPU fail-fast behavior, `training_log.json` sanity checks, held-out evaluation, and a new A/B gate before adapter promotion.
