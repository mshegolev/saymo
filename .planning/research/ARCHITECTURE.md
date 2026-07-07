# v1.8 Research: Call-ready Voice Clone Architecture

## Summary

v1.8 should integrate as a thin voice-readiness layer around the existing Saymo
runtime, not as a second playback stack. The current architecture already has
the right runtime seam: text is composed in `saymo/commands/core.py`, audio is
synthesized through `saymo/tts/factory.py`, and playback routes through the
existing BlackHole-safe paths, approved-draft paths, rehearsal checks, and
safety-soak gate. The milestone should keep those paths intact and add
inventory, profile, benchmark, selector, and voice-readiness contracts around
them.

Recommended direction: build a read-only asset inventory first, then a voice
profile/reference manifest, then benchmark/review artifacts, then a runtime
selector that chooses an approved engine chain before calling the existing TTS
factory. Rehearsal, `auto-preflight`, prepared response-cache generation,
approved-draft playback, and safety-soak should consume the same voice
readiness result. This keeps the live-call safety boundary centralized and
prevents benchmark-only code from leaking into production playback.

The most important boundary is fail-closed live playback. Preview and benchmark
commands may use experimental engines, but `prepare`, `speak`, `saymo auto`,
response-cache preparation, and `answer-cockpit action --action speak` should
only use a voice profile plus engine/fallback chain that has passed explicit
approval gates. Non-cloned fallbacks such as Piper or macOS `say` are useful for
diagnostics, but they should not silently reach the call unless the selected
profile marks them as call-ready fallbacks.

## Existing Components

| Component | Current Responsibility | v1.8 Reuse |
|-----------|------------------------|------------|
| `saymo/config.py` | Dataclass-backed YAML config with user-local `~/.saymo/config.yaml` precedence. Current TTS fields include `engine`, `realtime_engine`, `qwen3`, `f5tts`, `rvc`, and `voice_training`. | Extend `TTSConfig`; do not add ad hoc global config readers. |
| `saymo/tts/base.py` | Minimal `TTSEngine` protocol: `synthesize(text) -> bytes`, `stop()`. | Keep protocol small; implement fallback selection outside engines. |
| `saymo/tts/factory.py` | Single dispatch point for configured TTS engine; deferred imports protect optional dependencies. | Keep as engine constructor. Add a selector/wrapper above it instead of making callers import engines directly. |
| `saymo/tts/f5tts.py` | F5-TTS clone engine via isolated venv, checkpoint/vocab config, shared default voice sample, and optional reference text. | Reuse for F5 runtime and benchmark; pass profile-resolved `voice_sample`/`ref_text` instead of hardcoding defaults. |
| `saymo/tts/qwen3_tts.py` | Qwen3 clone engine via MLX with model and optional LoRA adapter. | Reuse as a candidate runtime engine once reference/profile resolution and benchmark gates exist. |
| `saymo/commands/core.py` | Main runtime paths: `prepare`, `speak`, `auto`, `_synthesize`, `_speak_text`, cache playback, live handbrake, approved call routing. | Modify only at narrow synthesis/preflight seams so playback, provider, and handbrake behavior remains unchanged. |
| `saymo/commands/tests.py` | Diagnostic/reliability commands: `test-tts`, `prepare-responses`, `auto-preflight`, `rehearsal`, `session-scorecard`, `safety-soak`, provider latency, trigger review, answer cockpit. | Add voice-readiness checks here or in a new command module following the same Click patterns. |
| `saymo/commands/voice_train.py` | Mutating voice-sample and training commands: record sample, prepare dataset, rebuild, train XTTS/Qwen3, A/B train eval. | Keep training/download work here and explicit. v1.8 profile/inventory commands should not call training implicitly. |
| `saymo/analysis/rehearsal.py` | Sanitized rehearsal artifact contracts and writer. Transcript is sanitized in JSON output. | Add voice-readiness checks to rehearsal artifacts without storing raw reference audio or full private text. |
| `saymo/analysis/safety_soak.py` | Aggregates sanitized scorecards, detects playback safety violations and drift, exits nonzero on failure. | Add voice-readiness and voice-cache invariants to the same gate. |
| `scripts/voice_clone_benchmark.py` | Current standalone shootout harness for F5 and Qwen3 Base dry-run/real runs. Writes WAV clips, `manifest.json`, and `blind-review.md`. | Promote core contracts into a reusable analysis module; keep the script as a thin CLI wrapper. |

## Proposed Components

| New/Modified Module | Type | Responsibility | Notes |
|---------------------|------|----------------|-------|
| `saymo/analysis/voice_inventory.py` | New | Read-only scan of voice samples, sidecar transcripts, training datasets, checkpoints, LoRA adapters, F5 venv/checkpoints, RVC/XTTS artifacts, response caches, and benchmark runs. | This is inventory only. It classifies assets as usable/missing/stale/protected but never deletes, trains, downloads, or rewrites. |
| `saymo/analysis/voice_profile.py` | New | Voice profile manifest contracts: profile id, reference audio path, reference text path/inline override, language, sample hash, approved engines, fallback approvals, benchmark links, created/updated timestamps. | Store under `~/.saymo/voice_profiles/<profile_id>/profile.json`. Prefer references plus hashes over copying expensive audio. |
| `saymo/analysis/voice_benchmark.py` | New | Reusable benchmark run/read/write/review contracts extracted from `scripts/voice_clone_benchmark.py`. | Script should call this module. Add `review.json` and `approval.json` beside existing `manifest.json` and `blind-review.md`. |
| `saymo/analysis/voice_readiness.py` | New | Compute a single `VoiceReadinessReport` for runtime gates: selected profile, engine chain, reference status, benchmark approval, cache fingerprint, live eligibility, warnings/blockers. | Consumed by preflight, rehearsal, response-cache preparation, approved playback, and safety-soak. |
| `saymo/tts/selector.py` | New | Resolve purpose-specific engine chain and synthesize with approved fallbacks while still instantiating engines through `get_tts_engine`. | Purposes: `preview`, `prepare`, `response_cache`, `realtime`, `approved_live`. Live purposes fail closed when no approved call-ready engine exists. |
| `saymo/commands/voice_clone.py` | New | User-facing commands: `voice-inventory`, `voice-profile`, `voice-benchmark`, `voice-preview`, `voice-ab`, `voice-readiness`. | Keep separate from `voice_train.py` so read-only/profile/approval operations are not mixed with training. Import this module from command registration. |
| `saymo/config.py` | Modified | Add typed config for voice profiles, fallback chains, benchmark thresholds, and approval behavior. | Keep config dataclass style and user-local precedence. Update `config.example.yaml`. |
| `saymo/tts/factory.py` | Modified | Accept optional resolved engine override or copied config from selector, but remain single-engine construction. | Do not embed fallback policy here; selector owns policy. |
| `saymo/commands/core.py` | Modified | Route `_synthesize`, `_speak_text`, `prepare`, and auto live fallback synthesis through `tts.selector.synthesize_with_fallback`. | Keep `_play_cached_audio`, provider automation, handbrake checks, and cache playback unchanged. |
| `saymo/commands/tests.py` | Modified | Add voice checks to `_collect_auto_preflight`, rehearsal, `session-scorecard`, `safety-soak`, and `prepare-responses`. | The same readiness report should power all gates. |
| `saymo/analysis/response_cache.py` and cache helpers | Modified | Include voice profile/engine fingerprint in cache metadata or namespace. | Prevent stale clips from an old engine/profile being treated as call-ready. |

## Data Flow

1. **Inventory:** `saymo voice-inventory` calls `voice_inventory.scan()` and prints a local report. It reads configured and conventional paths such as `~/.saymo/voice_samples`, `~/.saymo/training_dataset*`, `~/.saymo/models`, `~/F5TTS`, and `~/.saymo/voice_benchmarks`. It may write an optional report JSON, but it never mutates source assets.

2. **Profile/reference setup:** `saymo voice-profile create/set-reference` creates or updates a profile manifest that points to an existing reference WAV and transcript sidecar or configured reference text. The command records duration, sample rate, file size, and SHA-256 so later gates can detect drift. It does not copy, trim, or train unless a separate explicit recording/training command is run.

3. **Benchmark shootout:** `saymo voice-benchmark run --profile <id> --engine <engine>` resolves the profile reference, then uses `voice_benchmark` to generate clips through candidate engines. The existing script remains usable but delegates to the same module. Each run writes:
   - `manifest.json`: engine, profile id, reference hash, clip paths, latency, engine settings, dependency status.
   - `blind-review.md`: randomized listening order.
   - `review.json`: user-entered scores for similarity, naturalness, pronunciation, artifacts, and call readiness.
   - `approval.json`: explicit approval tying a profile id, engine key, fallback role, manifest hash, and reviewer decision together.

4. **Selector configuration:** Once approved, `voice-profile approve` records the approved engine/fallback role in the profile manifest and optionally updates `config.yaml` to point at the active profile and chain. Runtime commands do not infer approval merely from a benchmark run existing.

5. **Cache preparation:** `saymo prepare` and `saymo prepare-responses` synthesize through `tts.selector` for purpose `prepare`/`response_cache`. Cached audio gets a sidecar or namespace containing profile id, reference hash, engine key, fallback level, and selector fingerprint. `auto-preflight` fails or warns when cached audio does not match the active approved voice profile.

6. **Preview/A-B:** `saymo voice-preview` and `saymo voice-ab` synthesize to monitor/preview routes first. These commands may use experimental engines because they do not reach the call output unless the user explicitly asks for live playback and the readiness gate passes.

7. **Runtime playback:** `speak`, `auto`, and `answer-cockpit action --action speak` continue using the existing playback and provider code. Their only v1.8 change is synthesis/eligibility: before audio generation or approved-draft playback, they ask `voice_readiness` whether the selected profile/engine/cache is call-ready. The handbrake, approval, timeout, and provider gates remain the final runtime boundary.

8. **Rehearsal and soak:** `rehearsal` adds voice-readiness checks into `RehearsalCheck`. `session-scorecard` and `safety-soak` include voice profile, engine, cache fingerprint, benchmark approval, and fallback status as sanitized metrics. `safety-soak` fails on stale/unapproved engines or unexpected non-call-ready fallbacks.

## Config/Artifacts

Recommended config additions in `saymo/config.py`:

```python
@dataclass
class VoiceProfileConfig:
    active: str = "default"
    profiles_dir: str = ""  # defaults to ~/.saymo/voice_profiles
    require_call_ready_approval: bool = True


@dataclass
class VoiceFallbackConfig:
    prepare_chain: list[str] = field(default_factory=list)
    response_cache_chain: list[str] = field(default_factory=list)
    realtime_chain: list[str] = field(default_factory=list)
    approved_live_chain: list[str] = field(default_factory=list)
    preview_chain: list[str] = field(default_factory=list)
    allow_non_clone_live_fallback: bool = False


@dataclass
class VoiceBenchmarkConfig:
    out_root: str = ""  # defaults to ~/.saymo/voice_benchmarks
    min_similarity: float = 4.0
    min_naturalness: float = 4.0
    max_realtime_latency_ms: int = 2500
```

Add these under `TTSConfig`:

```python
voice_profile: VoiceProfileConfig = field(default_factory=VoiceProfileConfig)
fallbacks: VoiceFallbackConfig = field(default_factory=VoiceFallbackConfig)
benchmark: VoiceBenchmarkConfig = field(default_factory=VoiceBenchmarkConfig)
```

Example user config shape:

```yaml
tts:
  engine: f5tts_clone
  realtime_engine: qwen3_clone
  voice_profile:
    active: default
    require_call_ready_approval: true
  fallbacks:
    prepare_chain: [f5tts_clone, qwen3_clone]
    response_cache_chain: [f5tts_clone]
    approved_live_chain: [f5tts_clone]
    preview_chain: [f5tts_clone, qwen3_clone, macos_say]
    allow_non_clone_live_fallback: false
```

Primary artifacts:

| Artifact | Owner | Contents | Mutation Rule |
|----------|-------|----------|---------------|
| `~/.saymo/voice_profiles/<id>/profile.json` | `voice_profile.py` | Reference paths, hashes, language, approved engines/fallbacks, approval links. | Created/updated only by explicit profile commands. |
| `~/.saymo/voice_benchmarks/<timestamp>-<engine>/manifest.json` | `voice_benchmark.py` | Clip records, latency, settings, profile/reference hash, dependency status. | Written incrementally during benchmark. |
| `~/.saymo/voice_benchmarks/<timestamp>-<engine>/review.json` | `voice_benchmark.py` | User scores and notes per clip. | Written by review command. |
| `~/.saymo/voice_benchmarks/<timestamp>-<engine>/approval.json` | `voice_benchmark.py` / `voice_profile.py` | Explicit call-ready approval or rejection. | Written only by approval command. |
| `~/.saymo/audio_cache/.../*.voice.json` | response/prepared cache | Profile id, engine, fallback level, reference hash, selector fingerprint. | Written with generated audio; checked before live use. |
| Rehearsal/scorecard/soak JSON | existing analysis modules | Sanitized voice readiness summary and blockers. | No raw reference transcript or audio. |

## Safety Boundaries

| Boundary | Allowed | Blocked by Default |
|----------|---------|--------------------|
| Inventory | Read paths, hash files, classify missing/stale/protected assets, emit report. | Delete, move, deduplicate, train, download, or rewrite assets. |
| Profile | Reference existing voice samples/datasets, store hashes, point to transcript sidecars, mark approvals. | Use call recordings as training data, copy/trim audio implicitly, overwrite training datasets. |
| Benchmark | Generate new benchmark clips, write manifests/review/approval files, run dry-run gates. | Install/download heavy models without explicit command, mutate runtime config during a benchmark, hide failed clips. |
| Runtime Selector | Choose approved engine chain per purpose, call `get_tts_engine`, record fallback use, fail closed for live purposes. | Silently fall back to macOS/Piper in a live call, bypass the approved-draft gate, instantiate engines directly in commands. |
| Response Cache | Cache audio with profile/engine fingerprint, detect stale profile or engine drift. | Reuse old cache audio after profile/reference/engine changes without warning/failure. |
| Rehearsal | Show voice readiness as pass/warn/fail beside capture, trigger, hotkey, and playback gate checks. | Treat a successful trigger dry run as call-ready when the voice engine/profile is unapproved. |
| Safety Soak | Fail on unapproved/stale voice profile, stale cache, unexpected fallback, unsafe playback, or benchmark drift. | Store raw private transcript/reference text or perform destructive cleanup. |

The runtime should treat voice approval like existing answer approval: benchmark
generation proves that audio can be produced, but only a user approval artifact
allows it into the live-call route. If `require_call_ready_approval` is true and
no approved engine exists, live commands should produce a clear blocker and
suggest `voice-preview`/`voice-benchmark review`, not synthesize with a surprise
fallback.

## Suggested Build Order

1. **Read-only inventory contracts and CLI**
   - Add `voice_inventory.py` and `saymo voice-inventory`.
   - Cover F5, Qwen, XTTS, RVC, voice samples, datasets, benchmark runs, and caches.
   - Tests should create temp fake assets and prove no mutation happens.

2. **Voice profile/reference manifests**
   - Add `voice_profile.py`, config dataclasses, and `voice-profile status/create/set-reference`.
   - Resolve shared reference audio/text for F5 and Qwen without changing runtime playback yet.
   - Validate sidecar transcript handling and SHA drift detection.

3. **Benchmark contracts around the existing harness**
   - Extract manifest/review helpers from `scripts/voice_clone_benchmark.py` into `voice_benchmark.py`.
   - Keep script behavior compatible, add profile id/reference hash, and add review/approval artifacts.
   - Keep Qwen real execution gated until the known adapter risks are fixed.

4. **Selector and fallback chain**
   - Add `saymo/tts/selector.py` with `resolve_engine_chain` and `synthesize_with_fallback`.
   - Modify `_synthesize`, `_prepare_responses`, `_play_approved_draft_text`, and `test-tts` to use it where appropriate.
   - Keep `factory.py` as single-engine construction.

5. **Cache fingerprinting**
   - Add sidecar metadata or namespace paths for prepared standup audio and response-cache entries.
   - Update preflight to warn/fail on stale profile, stale reference hash, or fallback-generated cache.

6. **Preview/A-B approval commands**
   - Add `voice-preview`, `voice-ab`, `voice-benchmark review`, and `voice-profile approve`.
   - Default output to monitor/preview; live routing requires readiness pass.

7. **Reliability integration**
   - Add voice-readiness checks to `_collect_auto_preflight`, `rehearsal`, `session-scorecard`, and `safety-soak`.
   - Safety-soak should fail on unapproved live voice, stale cache, or unexpected fallback chain use.

8. **Documentation and regression tests**
   - Update `config.example.yaml`, CLI help, and voice-clone docs.
   - Add tests for inventory, profile drift, benchmark approval, selector fallback, stale cache blocking, and safety-soak failure cases.

Build in this order because each later phase depends on a stable artifact
contract from the prior phase. Runtime selector work should not start before
profiles and approvals exist; otherwise the milestone will recreate the current
risk: engines can synthesize audio, but the live system cannot prove which voice
is safe to put into a call.
