# v1.8 Research: Stack

## Summary

v1.8 should not replace Saymo's stack. It should add a small voice-readiness
layer around the existing Python CLI, TTS factory, BlackHole playback path,
rehearsal, safety-soak, response cache, and F5/Qwen benchmark harness.

The default call-ready baseline should remain `f5tts_clone` with the local
Russian F5 checkpoint already integrated through `saymo/tts/f5tts.py`. It is
the only candidate that is both wired into Saymo and documented as the current
shootout baseline. Qwen3-TTS Base should remain the first challenger, but only
through a dry-run-first benchmark gate and an isolated runtime. CosyVoice stays
blocked until F5 and Qwen3 have score reports.

The most important v1.8 stack addition is not another TTS library. It is local
asset discipline: inventory, voice profile metadata, benchmark manifests,
approval state, and explicit boundaries between protected source samples,
runtime model caches, generated benchmark clips, and production response audio.

Confidence: HIGH for repo-local recommendations, because they come from the
loaded v1.8 planning docs and current implementation. MEDIUM for external
package/version notes, because they are current as of 2026-07-07 from official
GitHub, Hugging Face, and PyPI pages but should be rechecked before install.

## Current Stack To Reuse

| Stack Piece | Reuse Decision | Evidence / Rationale |
|---|---|---|
| Python 3.11+, `uv`, Click, Rich, dataclass config | Reuse as-is | `pyproject.toml` and `saymo/config.py` already define the project shape. Do not add a second config framework. |
| Deferred TTS factory | Reuse and extend only at adapter boundaries | `saymo/tts/factory.py` centralizes engine selection and defers optional imports. New readiness code should call the factory or benchmark adapters, not import engines directly in CLI code. |
| `tts.engine` and `tts.realtime_engine` | Reuse for primary and realtime split | Existing config already supports a slower prepare-time engine and faster realtime override. v1.8 does not need a new runtime mode for this. |
| `f5tts_clone` | Keep as production baseline | `docs/voice-clone-shootout.md` names F5-TTS Russian as baseline; `saymo/tts/f5tts.py` runs it through isolated `~/F5TTS/.venv`; `scripts/install_f5tts.sh` records model paths in `~/.saymo/f5tts_model.txt`. |
| F5 Russian model assets | Reuse, inventory, do not move | Existing baseline paths are `~/F5TTS/models/ru/F5TTS_v1_Base_v2/model_last.pt` and `~/F5TTS/models/ru/F5TTS_v1_Base/vocab.txt`. The inventory should discover these paths rather than migrate them. |
| `scripts/voice_clone_benchmark.py` | Make it the canonical shootout harness | It already supports F5 and Qwen3 Base, shared Russian phrase set, dry-runs, reference transcript handling, per-clip latency, `manifest.json`, and `blind-review.md`. |
| `~/.saymo/voice_benchmarks/` | Reuse as benchmark artifact root | Existing docs and script write timestamped run directories here. Add score reports and approval metadata here rather than creating a parallel location. |
| `~/.saymo/voice_samples/voice_sample.wav` plus `.txt` | Reuse as default reference source | F5 and Qwen3 Base both require a reference WAV; Qwen3 real generation should fail fast without an exact transcript. |
| `~/.saymo/training_dataset*` | Read-only for v1.8 | v1.8 can inventory datasets and suggest readiness gaps, but training remains behind explicit commands and call recordings are not training material. |
| `saymo rehearsal`, `session-scorecard`, `safety-soak` | Reuse as readiness gates | v1.7 already provides local evidence artifacts and pass/fail checks. v1.8 should add voice-readiness checks into these commands instead of inventing a separate go-live flow. |
| `~/.saymo/audio_cache/responses/` | Reuse for production cached responses only | Benchmark clips should not be promoted into this cache until an explicit preview/A-B approval gate passes. |
| `piper` and `macos_say` | Keep as non-cloned emergency fallbacks | They are useful when cloned TTS is unavailable, but they should be labeled as "not user's voice" and not silently replace an approved clone in a real call. |

External source checks:

- F5-TTS official project recommends a separate environment and supports pip
  package installation for inference; current PyPI latest observed:
  `f5-tts 1.1.21`, released 2026-07-05.
  Source: https://github.com/SWivid/F5-TTS and https://pypi.org/project/f5-tts/
- `Misha24-10/F5-TTS_RUSSIAN` is a Russian fine-tune of F5-TTS, tagged for
  Russian voice cloning, with `F5TTS_v1_Base_v2` listed as the v2 variant.
  Source: https://huggingface.co/Misha24-10/F5-TTS_RUSSIAN
- Qwen3-TTS official docs list `Qwen3-TTS-12Hz-1.7B-Base` as the Base model
  for rapid voice clone from user audio and recommend a fresh isolated Python
  3.12 environment for `qwen-tts`.
  Source: https://github.com/QwenLM/Qwen3-TTS and https://pypi.org/project/qwen-tts/
- CosyVoice 3 official docs describe multilingual zero-shot voice cloning and
  streaming, but its install path requires a cloned repo, submodules, conda
  Python 3.10, and pretrained model downloads. This supports keeping it gated.
  Source: https://github.com/FunAudioLLM/CosyVoice

## Stack Additions

### 1. Voice Asset Inventory, No New Runtime Dependency

Add an internal inventory module, for example `saymo/tts/inventory.py` or
`saymo/voice/inventory.py`, using stdlib `pathlib`, `json`, `hashlib`,
`datetime`, and existing `soundfile` where duration/sample-rate inspection is
needed.

Inventory should report:

- configured `tts.engine`, `tts.realtime_engine`, and known engine availability;
- F5 venv path, F5 CLI path, checkpoint path, vocab path, model variant, and
  whether paths exist;
- Qwen runtime status without importing `qwen_tts` unless an explicit check is
  requested;
- protected local assets: `~/.saymo/voice_samples/`,
  `~/.saymo/training_dataset*`, trained model/adapters, response caches, and
  benchmark outputs;
- stale or duplicate candidates as "review only", never auto-delete.

Recommended output:

- CLI table for humans;
- JSON report under `~/.saymo/voice_inventory/<timestamp>.json`;
- sanitized summary that can be included in `session-scorecard` and
  `safety-soak`.

Do not add SQLite, TinyDB, Pydantic, platformdirs, or a file-indexing library
for this milestone. The existing `~/.saymo` layout and dataclass config are
enough.

### 2. Voice Profile Metadata

Add a small profile manifest layer for reference choices and approval state.
Recommended location:

```text
~/.saymo/voice_profiles/<profile>.json
```

Recommended fields:

```json
{
  "profile": "standup",
  "default_reference_wav": "~/.saymo/voice_samples/voice_sample.wav",
  "default_reference_text": "~/.saymo/voice_samples/voice_sample.txt",
  "approved_engine": "f5tts_clone",
  "approved_benchmark_run": "~/.saymo/voice_benchmarks/20260707-120000-f5tts",
  "fallback_policy": "require_confirmation_for_non_cloned_voice",
  "updated_at": "2026-07-07T00:00:00"
}
```

This manifest should reference assets, not copy them. Writes must be atomic and
must never rewrite reference WAVs or training datasets.

### 3. Benchmark Harness Extensions

Extend the existing `scripts/voice_clone_benchmark.py` instead of creating a
new harness.

Add:

- `score-report.md` next to `manifest.json` and `blind-review.md`;
- optional `review.json` with per-clip similarity, naturalness, Russian
  pronunciation, artifacts, and notes;
- `approved.json` or an approval field in the voice profile after explicit
  user approval;
- `--profile` to select reference/profile metadata;
- `--engine qwen3_base` real-run guard that refuses execution until the
  reference transcript is present and the Qwen environment is explicitly
  selected.

Keep:

- current Russian phrase set;
- incremental manifest writes after every clip;
- dry-run mode that does not import heavy packages or download models;
- `--limit 1` / `--limit 3` smoke runs for CPU.

### 4. Qwen3 Base Challenger Runtime

Keep Qwen3 Base out of Saymo's main `.venv` for v1.8.

Recommended isolated runtime:

```text
~/.saymo/runtimes/qwen3-base/.venv/
~/.saymo/models/qwen3/Qwen3-TTS-12Hz-1.7B-Base/
```

Use `qwen-tts` only after dry-run passes and after the F5 baseline has a score
report. Current official PyPI latest observed is `qwen-tts 0.1.1`, released
2026-02-06. Do not add `qwen-tts` to `pyproject.toml` yet.

Important boundary:

- `qwen3_base` benchmark uses the official `qwen_tts.Qwen3TTSModel` API and
  `Qwen/Qwen3-TTS-12Hz-1.7B-Base`.
- Existing Saymo `qwen3_clone` runtime uses `mlx_audio` and the CustomVoice
  path, and its LoRA training path is still not the v1.8 promotion path.

Do not conflate those two paths. v1.8 should benchmark Qwen3 Base zero-shot
before any LoRA or runtime default changes.

### 5. Call-ready Fallback Resolver

Add a small internal resolver around the existing factory rather than adding
new engines.

Recommended behavior:

1. Try the approved cloned engine from the voice profile or `tts.engine`.
2. If it fails in rehearsal/preflight, report a blocking readiness failure with
   exact missing asset/runtime paths.
3. In real-call paths, do not silently fall back to `piper` or `macos_say`
   unless the user has explicitly approved non-cloned fallback.
4. For cache-backed paths, prefer already prepared and approved audio over live
   synthesis.

This keeps the user from thinking Saymo is speaking in the cloned voice when it
has fallen back to a generic voice.

### 6. Rehearsal and Safety-soak Integration

Add voice-readiness checks to existing v1.7 commands:

- active engine exists and is known by `KNOWN_ENGINES`;
- required reference WAV and transcript exist;
- F5 venv/checkpoint/vocab exist for `f5tts_clone`;
- Qwen isolated runtime and local model directory exist before real Qwen runs;
- latest approved benchmark is present for the active voice profile;
- non-cloned fallback policy is visible;
- benchmark latency meets the call-ready gate, or response cache fallback is
  enabled and populated.

No new service or daemon is required.

## Internal PyPI/Nexus Notes

Do not hardcode internal package indexes in `pyproject.toml`, docs intended for
public users, or committed config. Use them as developer-local install
overrides when package resolution or public PyPI access is slow.

Recommended local command shape for approved installs:

```bash
UV_HTTP_TIMEOUT=120 UV_CONCURRENT_DOWNLOADS=1 \
  uv pip install \
  --index-url https://nexus3.int.rclabenv.com/repository/pypi-all/simple \
  <package>
```

Use this strategy for isolated runtimes only:

- `~/.saymo/runtimes/qwen3-base/.venv` for `qwen-tts`;
- existing `~/F5TTS/.venv` if F5 package reinstall is explicitly approved;
- future `~/.saymo/runtimes/cosyvoice/.venv` only after the CosyVoice gate
  opens.

Do not use the internal PyPI mirror as a model-weight strategy. Qwen, F5, and
CosyVoice weights are Hugging Face / ModelScope assets. For call readiness,
prefer explicit local model directories over runtime auto-downloads.

Before any approved install, verify whether the mirror has:

- `qwen-tts==0.1.1` or the then-current official package;
- compatible `torch`, `torchaudio`, `transformers`, and `soundfile` wheels for
  the target Python and macOS architecture;
- `f5-tts==1.1.21` or the currently installed known-good version, if F5 is
  being repaired.

If the package is not mirrored, pause with a clear install plan instead of
falling through to public PyPI silently.

## Model Storage Boundaries

Treat local voice state as three separate categories: protected source assets,
runtime assets, and generated artifacts.

### Protected Source Assets

Never delete, rewrite, normalize in place, or train from these without an
explicit command:

```text
~/.saymo/voice_samples/
~/.saymo/training_dataset*
~/.saymo/models/*_finetuned/
~/.saymo/models/qwen3_finetuned/
```

Inventory can read metadata, hash files, and check sidecars. Any cleanup should
only mark candidates for review.

### Runtime Assets

Runtime assets are rebuildable but expensive. Inventory them separately from
source voice assets:

```text
~/F5TTS/.venv/
~/F5TTS/models/ru/
~/.saymo/f5tts_model.txt
~/.saymo/runtimes/qwen3-base/.venv/
~/.saymo/models/qwen3/Qwen3-TTS-12Hz-1.7B-Base/
~/.cache/huggingface/hub/
~/.cache/modelscope/
```

Do not move the existing F5 runtime in v1.8. The inventory should understand
the legacy `~/F5TTS` boundary and recommend future runtimes under
`~/.saymo/runtimes/`.

### Generated Artifacts

Generated outputs can be regenerated, but should still be retained for audit
until the user cleans them:

```text
~/.saymo/voice_benchmarks/<run_id>/
~/.saymo/voice_inventory/<timestamp>.json
~/.saymo/voice_profiles/<profile>.json
~/.saymo/audio_cache/responses/
~/.saymo/rehearsals/<profile>/
```

Promotion rule:

- benchmark WAVs stay in `voice_benchmarks`;
- approved production response WAVs go through the existing response-cache
  preparation path;
- generated test clips never become live-call audio just because they exist.

## Do Not Add

- No required cloud TTS/STT or hosted voice-cloning APIs.
- No ElevenLabs, PlayHT, Azure voice, or similar cloud voice path for v1.8.
- No database, vector store, object store, or background indexing service for
  voice assets.
- No new GUI, web app, menu bar app, LaunchAgent, or meeting bot.
- No required CosyVoice install until a Qwen3 Base score report exists and
  shows Qwen was blocked or lost.
- No GPT-SoVITS, Fish Speech, Chatterbox, OpenVoice, or XTTS/RVC/Applio
  reinstall in this pass.
- No Qwen3 LoRA training work in v1.8. The zero-shot Base gate comes first.
- No `qwen-tts`, `f5-tts`, or CosyVoice packages in Saymo's main dependencies
  yet. Keep candidate stacks isolated.
- No automated deletion of `~/.saymo/voice_samples`, `training_dataset*`,
  model checkpoints, or adapters.
- No hidden runtime model downloads from `saymo auto`, `saymo speak`, rehearsal,
  or safety-soak. Those commands should fail with actionable instructions.
- No silent fallback from cloned voice to generic voice during a live call.
- No objective MOS/deep-audio scoring stack before manual blind A/B is working.
  The current roadmap needs reproducible artifacts and user approval first.

## Open Questions

1. Should v1.8 introduce a committed config field for `voice_profile`, or keep
   voice profiles as CLI-selected local manifests only?
2. Should future isolated runtimes standardize on `~/.saymo/runtimes/<engine>/`
   even though F5 already lives in `~/F5TTS`?
3. Does the internal Nexus mirror currently contain `qwen-tts 0.1.1` and
   macOS-compatible transitive wheels, or will Qwen need a one-off public PyPI
   approval?
4. Should Qwen3 Base benchmark support both official `qwen_tts` and local model
   directories from day one, or require model id first and add local-directory
   support after the first real run?
5. What is the explicit policy for non-cloned fallback in real calls: block
   speech, ask for confirmation, or allow only for prepared standup fallback?
6. F5 Russian model license is `cc-by-nc-4.0` on Hugging Face while the F5 code
   package is MIT. For private local use this is probably acceptable, but any
   redistributed or commercial packaging needs a license decision before
   promotion language says "default".
