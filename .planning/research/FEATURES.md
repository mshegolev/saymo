# v1.8 Research: Call-ready Voice Clone Features

## Summary

v1.8 should make the cloned-voice path trustworthy, reproducible, and safe for
real calls. The user-facing product should not feel like "install another TTS
engine"; it should feel like a local call-readiness workflow: inspect what
voice assets exist, choose or create a protected voice profile, benchmark
candidate engines with the same prompts and references, approve a winner by
listening, then let `prepare`, `speak`, `rehearsal`, and `safety-soak` enforce
that approval.

The milestone should preserve current workflows:
`saymo record-voice`, `saymo train-prepare`, `saymo train-voice`,
`saymo train-eval`, `saymo test-tts`, `saymo prepare`, `saymo review`,
`saymo speak`, `saymo rehearsal`, `saymo session-scorecard`, and
`saymo safety-soak` remain valid. New v1.8 capabilities should add evidence
and gates around those commands, not replace them with a heavy UI.

The default behavior must be read-only and local. Inventory, profile setup,
benchmark dry-runs, review, and reports may inspect local files and write
small metadata artifacts under `~/.saymo/`, but they must not delete assets,
start training, install packages, or download models without an explicit user
command. A cloned voice must not be routed to a real call output until preview
or A/B approval evidence exists.

## Table Stakes

| Feature | User-facing behavior | Expected commands / entry points | Testable outcome |
|---|---|---|---|
| Voice asset inventory | User can see all local voice-related assets: active engine config, F5 checkpoints, Qwen support status, XTTS fine-tune artifacts, reference WAV/TXT, training datasets, benchmark runs, caches, and likely-safe vs protected state. Inventory is read-only. | New: `saymo voice-inventory`, `saymo voice-inventory --json-output ~/.saymo/voice_inventory.json`. Preserve: `saymo train-status`, `saymo test-voice-sample`. | Command exits 0 without mutating files; report marks protected assets such as `~/.saymo/voice_samples/` and `~/.saymo/training_dataset*`; JSON includes path, exists, size, role, engine, and status. |
| Voice reference/profile setup | User can bind a meeting profile to a known local reference sample, transcript sidecar, dataset, and intended engine without rewriting the sample or dataset. | New: `saymo voice-profile init -p personal --voice-sample ~/.saymo/voice_samples/voice_sample.wav --ref-text-file ~/.saymo/voice_samples/voice_sample.txt --engine f5tts_clone --dry-run`; `saymo voice-profile show -p personal`; `saymo voice-profile init ... --apply`. | Dry-run prints proposed profile and performs no writes; `--apply` writes only metadata under `~/.saymo/voice_profiles/<profile>.json`; profile starts `approved_for_calls=false`. |
| Reference quality gate | User gets a concrete pass/warn/fail for the reference WAV before benchmarks or calls: exists, duration, peak level, sample rate, transcript sidecar availability, and obvious clipping/too-quiet issues. | Extend `saymo test-voice-sample`; new or integrated `saymo voice-profile check -p personal`. | Missing/short/quiet reference returns not-ready; valid sample returns ready; report gives the smallest rerun command such as `saymo record-voice -d 12`. |
| Reproducible benchmark shootout | User can generate comparable clips for each candidate engine using the same phrase set and reference input. Partial runs are useful and persist artifacts. | Preserve script: `uv run python scripts/voice_clone_benchmark.py --engine f5tts --limit 3 --f5-nfe-step 16`; `uv run python scripts/voice_clone_benchmark.py --engine qwen3_base --limit 1 --dry-run`. Optional wrapper: `saymo voice-benchmark run --engine f5tts`. | Run directory under `~/.saymo/voice_benchmarks/<timestamp>-<engine>/` contains WAVs, `manifest.json`, and `blind-review.md`; manifest records engine settings and per-clip latency; dry-run creates shape-compatible artifacts without imports/downloads. |
| Baseline-first candidate sequence | User benchmarks F5 Russian first, then Qwen3 Base only after the dry-run gate, then later candidates only if earlier candidates fail. | `uv run python scripts/voice_clone_benchmark.py --engine f5tts --limit 10 --f5-nfe-step 16`; then `--engine qwen3_base --dry-run`; then real Qwen only with `--ref-text-file`. | Qwen real generation fails fast without reference transcript; dry-run never imports `qwen_tts`; production `tts.engine` is unchanged by benchmark commands. |
| Blind review and approval | User can listen without engine bias, record scores, and approve a winner only when it meets the promotion gate. | Existing artifact: `blind-review.md`. New: `saymo voice-benchmark review <run-dir>` and `saymo voice-benchmark score <run-dir> --baseline <f5-run-dir>`; approval via `saymo voice-profile approve -p personal --benchmark-run <run-dir> --winner f5tts`. | Approval artifact stores run id, engine, reviewer decision, score summary, timestamp, and gate result; promotion requires at least 7/10 similarity wins or an explicit override flag that is visible in the report. |
| Call-ready engine and fallback chain | User can choose the default call voice plus fallback behavior for prepared playback and real-time approved drafts. Fallbacks are explicit and visible. | New: `saymo voice-profile activate -p personal --engine f5tts_clone --fallback coqui_clone,piper,macos_say --dry-run`; config still uses `tts.engine` and `tts.realtime_engine` where applicable. | `saymo prepare -p personal` uses the active approved engine; if synthesis fails, fallback order is logged; reports show which engine produced each clip. |
| Existing pre-call gates include voice readiness | User sees voice approval status before trusting `speak` or `auto`. Rehearsal and safety soak fail when the cloned voice is not approved for call output. | Extend `saymo auto-preflight -p personal`, `saymo rehearsal -p personal --text "..."`, `saymo safety-soak -p personal ...`. | Preflight includes `voice profile`, `reference sample`, `approved engine`, `fallback chain`, and `last benchmark`; safety-soak exits nonzero when call route would use an unapproved cloned engine. |
| Preview-before-call enforcement | User can preview cloned voice locally, but Saymo refuses to route cloned voice to BlackHole/provider call output before approval evidence exists. | Preserve: `saymo test-tts "..."`, `saymo review`, `saymo answer-cockpit action ... --preview`. Enforce for: `saymo speak --provider ...`, `saymo auto`, non-preview `answer-cockpit action --action speak`. | Preview routes are allowed with `approved_for_calls=false`; provider/BlackHole call routes are blocked with a clear message and remediation command. |
| Sanitized evidence reports | User can export voice-readiness evidence without raw audio or private transcript text. | New: `saymo voice-readiness -p personal -o ~/.saymo/voice_readiness/personal.md --json-output ~/.saymo/voice_readiness/personal.json`. | Markdown/JSON includes engine, asset fingerprints, readiness, benchmark run ids, latency summary, approval state, and fallback chain; it omits raw WAV content and private config secrets. |
| Integration with current prepared/live flows | Existing `prepare`, `speak`, response cache, approved draft playback, and live fallback paths use the same approved profile and fallback policy. | Preserve: `saymo prepare -p personal`; `saymo prepare-responses`; `saymo speak -p personal --provider glip`; `saymo answer-cockpit action --action speak`. | Prepared cache artifacts record voice engine/profile metadata; approved draft playback uses `tts.realtime_engine` only when that engine is approved or preview-only. |

## Differentiators

| Feature | Value proposition | Testable outcome |
|---|---|---|
| Protected local voice inventory | Saymo treats voice samples, datasets, and checkpoints as expensive user-owned assets, not disposable cache. | Inventory marks protected assets and never deletes them; destructive cleanup remains outside v1.8 and requires a separate explicit command. |
| Evidence-backed engine promotion | The product promotes engines only after reproducible local benchmark artifacts and human listening approval, not by default claims or single synthetic metrics. | `voice-profile approve` requires a benchmark run id and stores the gate result; `tts.engine` is not changed by benchmark generation alone. |
| Call safety tied to voice quality | Voice approval becomes part of the same safety system as trigger checks, rehearsal, scorecards, and safety soak. | A pre-call safety report can explain both "will Saymo speak at the right time?" and "is this cloned voice approved for the call route?" |
| CPU-only MVP with optional GPU challengers | The user can have a call-ready path on CPU via F5/prepared cache while Qwen3/CosyVoice/GPT-SoVITS remain gated challengers. | F5 benchmark and prepared playback work without Qwen packages; Qwen dry-run validates wiring before any install/download. |
| Benchmark artifacts survive interruptions | Long CPU runs still produce useful partial evidence. | `manifest.json` and `blind-review.md` update after each successful clip; rerunning can compare completed clips instead of starting research from zero. |
| Voice profile provenance | The user can answer "which voice, which reference, which model, which benchmark, which fallback?" before a call. | `voice-profile show` and readiness JSON include profile id, engine, reference fingerprint, benchmark run, approval state, and fallback chain. |
| Review-first live-call illusion | Saymo preserves the user's voice illusion by preventing unreviewed, poor, or wrong-engine output from reaching the call. | Real-call route is blocked until preview/A-B evidence exists; manual takeover and macOS/Piper fallback remain available. |

## Anti-Features

| Anti-feature | Why avoid | What to do instead |
|---|---|---|
| Automatic deletion of voice/model assets | Voice samples, datasets, and checkpoints are costly to recreate and may be the only usable voice identity source. | Inventory may classify assets; deletion must remain a separate explicit cleanup flow with confirmation. |
| Benchmark command that installs or downloads models by default | The user explicitly needs dry-run-first gates and no unapproved heavy downloads. | Dry-run Qwen/Cosy challengers first; real runs fail with clear install/transcript prerequisites. |
| Training started implicitly by setup, profile init, benchmark, or preflight | Training is long, expensive, and changes model state. | Reuse existing `saymo train-prepare`, `saymo train-voice`, `saymo train-qwen3`, and require explicit invocation. |
| Using real call recordings as voice-clone training data | Existing call capture is for trigger/reliability review, not voice identity training; consent and quality risks are high. | Use deliberate clean `record-voice` / `train-prepare` recordings; defer call-audio export to a future explicit feature. |
| Auto-speaking cloned voice into a real call before approval | Bad clone quality breaks trust and can expose automation accidentally. | Allow local preview; block provider/BlackHole call output until an approval artifact exists. |
| Changing production `tts.engine` during benchmark generation | Benchmarks should be experiments, not configuration mutations. | Keep overrides in benchmark run settings; activate a winner only through explicit profile activation. |
| Cloud TTS/STT as required path | Saymo's core value is local-by-default privacy and offline control. | Keep cloud providers optional and outside the call-ready clone gate. |
| Native GUI or menu bar for v1.8 | The current risk is voice evidence and routing safety, not UI discoverability. | Add CLI reports and reuse existing TUI/handbrake surfaces. |
| Fully automatic MOS/similarity scoring as the promotion authority | Objective voice metrics can miss user-perceived identity and artifacts. | Use manual blind A/B as the required gate; optional metrics can supplement later. |
| Requiring Qwen3/CosyVoice/GPU for call readiness | This would block CPU-only users despite the existing F5/prepared-cache path. | Ship F5 baseline first; treat GPU engines as challengers or real-time enhancements. |

## Suggested User Workflows

### 1. Audit Existing Voice State

```bash
saymo train-status
saymo test-voice-sample
saymo voice-inventory --json-output ~/.saymo/voice_inventory.json
```

Expected outcome: the user sees active config, protected voice samples,
datasets, candidate engines, existing benchmarks, and concrete blockers such
as missing F5 checkpoint, missing reference transcript, or too-quiet WAV.

### 2. Create A Read-only Voice Profile

```bash
saymo voice-profile init -p personal \
  --voice-sample ~/.saymo/voice_samples/voice_sample.wav \
  --ref-text-file ~/.saymo/voice_samples/voice_sample.txt \
  --engine f5tts_clone \
  --dry-run

saymo voice-profile init -p personal \
  --voice-sample ~/.saymo/voice_samples/voice_sample.wav \
  --ref-text-file ~/.saymo/voice_samples/voice_sample.txt \
  --engine f5tts_clone \
  --apply

saymo voice-profile check -p personal
```

Expected outcome: only profile metadata is written; source WAV/TXT/datasets are
unchanged; profile is usable for benchmarks but not approved for call output.

### 3. Establish F5 Baseline

```bash
uv run python scripts/voice_clone_benchmark.py \
  --engine f5tts \
  --limit 3 \
  --f5-nfe-step 16

uv run python scripts/voice_clone_benchmark.py \
  --engine f5tts \
  --f5-nfe-step 16
```

Expected outcome: smoke run verifies setup quickly; full run creates ten WAVs,
latencies, `manifest.json`, and `blind-review.md` under
`~/.saymo/voice_benchmarks/`.

### 4. Gate Qwen3 Base Challenger

```bash
uv run python scripts/voice_clone_benchmark.py \
  --engine qwen3_base \
  --limit 1 \
  --dry-run

uv run python scripts/voice_clone_benchmark.py \
  --engine qwen3_base \
  --ref-text-file ~/.saymo/voice_samples/voice_sample.txt
```

Expected outcome: dry-run validates output shape without importing Qwen or
downloading models. Real generation requires an explicit transcript and fails
fast if prerequisites are missing.

### 5. Review And Approve The Winner

```bash
saymo voice-benchmark review ~/.saymo/voice_benchmarks/<run>
saymo voice-benchmark score ~/.saymo/voice_benchmarks/<challenger-run> \
  --baseline ~/.saymo/voice_benchmarks/<f5-run>

saymo voice-profile approve -p personal \
  --benchmark-run ~/.saymo/voice_benchmarks/<winning-run> \
  --winner f5tts_clone
```

Expected outcome: approval is backed by a stored benchmark run and listening
decision. If the winner does not meet the 7/10 similarity gate, the profile
stays not approved unless the user records an explicit override.

### 6. Activate For Prepared Playback With Fallbacks

```bash
saymo voice-profile activate -p personal \
  --engine f5tts_clone \
  --fallback coqui_clone,piper,macos_say \
  --dry-run

saymo voice-profile activate -p personal \
  --engine f5tts_clone \
  --fallback coqui_clone,piper,macos_say \
  --apply
```

Expected outcome: activation updates only approved voice profile/config fields;
fallback order is visible; production config is not changed by benchmark runs.

### 7. Pre-call Voice Readiness Gate

```bash
saymo prepare -p personal
saymo review
saymo auto-preflight -p personal
saymo rehearsal -p personal --text "Your Name, what is the status?"
saymo safety-soak -p personal \
  --rehearsal ~/.saymo/rehearsals/personal/<artifact>.json \
  --json-output ~/.saymo/voice_readiness/soak.json
```

Expected outcome: preflight/rehearsal/soak include voice approval, benchmark,
reference, and fallback checks. The gate fails before a real call if the cloned
voice is not approved for call output.

### 8. Real-call Use After Approval

```bash
saymo speak -p personal --provider glip
saymo auto -p personal
```

Expected outcome: Saymo speaks only through an approved cloned engine or an
explicit fallback; playback logs show engine/profile/fallback source; handbrake
and manual takeover behavior remain unchanged.

## Deferred Capabilities

| Capability | Defer because |
|---|---|
| Automatic model cleanup/deletion | Requires a separate destructive-command UX and confirmations; v1.8 should inventory, not delete. |
| Automatic installation of Qwen3/CosyVoice/GPT-SoVITS | Heavy downloads should remain explicit after dry-run gates prove the command path. |
| Qwen3 LoRA as a required v1.8 path | Existing Qwen LoRA training still has implementation risk; zero-shot benchmark plus F5 call readiness is the safer milestone scope. |
| GPT-SoVITS fine-tune | Candidate order says use only if zero-shot candidates fail; it adds training complexity and more moving parts. |
| Training from live call recordings | Privacy, consent, speaker leakage, and audio-quality risks need a separate export/review milestone. |
| Native GUI/menu bar voice manager | CLI/TUI evidence and gates are enough for v1.8; UI can come after the workflow proves useful. |
| Automatic objective voice scoring as approval | Speaker embeddings/MOS estimates may help later, but blind A/B approval remains the reliable user gate now. |
| Cross-machine voice profile sync | Voice assets are local/private and large; syncing raises security and reproducibility questions outside this milestone. |
| Defaulting `responses.live_fallback=true` for everyone | Live synthesis latency and quality vary by engine/hardware; keep prepared/cache path as default and make live fallback opt-in. |
| Cloud voice clone providers | Conflicts with local-only default and privacy posture; can remain an optional future comparison, not a v1.8 requirement. |
