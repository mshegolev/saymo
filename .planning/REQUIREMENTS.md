# Requirements: Saymo v1.8 Call-ready Voice Clone

**Defined:** 2026-07-07
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.8 Requirements

Requirements for milestone v1.8 Call-ready Voice Clone.

### Voice Asset Inventory

- [ ] **INV-01**: User can run a read-only voice inventory that reports active
  engine config, known TTS engines, F5 paths, Qwen support status, XTTS/RVC
  remnants, voice samples, transcript sidecars, training datasets, response
  caches, and benchmark runs.
- [ ] **INV-02**: User can see each local voice asset classified as usable,
  missing, stale, duplicate, protected, dangerous to delete, or requiring user
  action without any file deletion or mutation.
- [ ] **INV-03**: User can export sanitized inventory JSON/Markdown that
  includes paths, sizes, hashes or fingerprints where useful, and roles, while
  omitting private transcript text and secrets.
- [ ] **INV-04**: Inventory and profile checks treat `~/.saymo/voice_samples`,
  `~/.saymo/training_dataset*`, trained adapters, and F5 runtime assets as
  protected local state.

### Voice Profile and Reference Setup

- [ ] **PROF-01**: User can create or update a voice profile that references an
  existing WAV and transcript sidecar without copying, rewriting, trimming, or
  retraining from those assets.
- [ ] **PROF-02**: User can validate a profile reference for existence,
  duration, sample rate, channel count, sidecar transcript availability,
  clipping/too-quiet risk, and SHA/hash drift.
- [ ] **PROF-03**: User can inspect voice profile status, active engine,
  reference fingerprint, approval state, fallback policy, and linked benchmark
  runs.
- [ ] **PROF-04**: Any profile mutation is explicit and atomic; dry-run profile
  commands show proposed changes without writing.

### Benchmark and Baseline Evidence

- [ ] **BEN-01**: User can run F5 benchmark dry-run, smoke, and full baseline
  runs with the existing Russian phrase set, stable phrase ids, reference
  metadata, per-clip latency, and incremental manifest writes.
- [ ] **BEN-02**: User can produce benchmark artifacts under
  `~/.saymo/voice_benchmarks/<run_id>/`: WAV clips, `manifest.json`,
  `blind-review.md`, `review.json`, and `score-report.md`.
- [ ] **BEN-03**: User can score benchmark clips for similarity, naturalness,
  Russian pronunciation, artifacts, notes, and call-readiness without leaking
  private reference transcript text.
- [ ] **BEN-04**: Benchmark reports clearly mark runs as dry-run, partial,
  complete, rejected, or approved and preserve useful evidence after
  interrupted long runs.
- [ ] **BEN-05**: F5 baseline score evidence exists before any challenger can
  be treated as a promotion candidate.

### Candidate Engine Gates

- [ ] **CAND-01**: User can run Qwen3 Base dry-run without importing
  `qwen_tts`, installing packages, downloading model weights, or changing
  production config.
- [ ] **CAND-02**: User can run real Qwen3 Base benchmark only when a reference
  transcript is provided through `--ref-text`, `--ref-text-file`, or sidecar
  `.txt`, and the command fails fast otherwise.
- [ ] **CAND-03**: Qwen3 Base benchmark evidence is kept separate from the
  existing production `qwen3_clone` MLX runtime until runtime readiness is
  proven explicitly.
- [ ] **CAND-04**: CosyVoice, GPT-SoVITS, LoRA training, and other heavier
  candidates remain blocked until earlier score reports justify opening the
  next gate.
- [ ] **CAND-05**: Approved installs use an explicit, documented isolated
  runtime plan, preferring the internal Nexus3 PyPI mirror when package
  resolution is needed, without hardcoding the mirror into public config.

### Call Runtime Selector and Fallback

- [ ] **RUN-01**: User can configure an approved engine and fallback chain per
  purpose: preview, prepare, response cache, realtime, and approved live call.
- [ ] **RUN-02**: Runtime synthesis routes through one selector that uses the
  existing TTS factory and records selected engine, attempted engine, fallback
  engine, cloned-vs-non-cloned state, and blocked reason.
- [ ] **RUN-03**: `prepare`, `prepare-responses`, `speak`, approved draft
  playback, and `auto` use voice profile and fallback readiness without
  bypassing existing handbrake, approval, timeout, and provider safety gates.
- [ ] **RUN-04**: Cached prepared audio and response-cache entries include
  voice profile, reference fingerprint, engine, fallback, and selector
  metadata so stale voice audio cannot be silently treated as current.
- [ ] **RUN-05**: Non-cloned fallbacks such as Piper and macOS `say` are
  visible and blocked for live-call output unless explicitly approved as
  non-cloned fallback behavior.

### Preview, Approval, and Safety Gates

- [ ] **SAFE-01**: User can preview cloned voice locally or on the configured
  monitor route before call approval, with audit metadata marking the output
  as preview-only.
- [ ] **SAFE-02**: User can approve or reject a voice profile/engine only by
  linking benchmark score evidence and recording whether the 7/10 similarity
  and artifact gates passed or were explicitly overridden.
- [ ] **SAFE-03**: Real call output through `speak`, approved draft playback,
  hotkey-triggered speak, or `auto` is blocked when the active voice profile,
  benchmark approval, reference fingerprint, or cache fingerprint is missing,
  stale, or unapproved.
- [ ] **SAFE-04**: `auto-preflight`, `rehearsal`, `session-scorecard`, and
  `safety-soak` include voice readiness, selected engine, benchmark approval,
  fallback status, cache fingerprint, and remediation hints.
- [ ] **SAFE-05**: Safety-soak fails when unapproved cloned audio, stale cache,
  unexpected non-cloned fallback, manual takeover, hard-disable, or unapproved
  generated draft conditions would allow unsafe live playback.

## Future Requirements

Deferred beyond v1.8.

### Fine-tuning and New Candidates

- User can run Qwen3 LoRA or GPT-SoVITS fine-tuning after zero-shot candidates
  and dataset quality evidence justify the training cost.
- User can install and benchmark CosyVoice after Qwen3 score reports show that
  the next candidate gate should open.
- User can export selected live-call recordings into a separate consented
  voice-training dataset after privacy and speaker-leakage safeguards exist.

### Packaging and UI

- User can manage voice profiles, benchmark runs, and approvals from a native
  or browser UI after CLI artifacts stabilize.
- User can sync or back up voice profiles across machines with encryption and
  explicit handling of large private assets.

### Automated Scoring

- User can add optional speaker-embedding or MOS-like scoring as supplemental
  evidence after manual blind A/B approval remains the authority.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automatic deletion or deduplication of voice/model assets | v1.8 inventories protected assets; destructive cleanup needs a separate explicit flow. |
| Training started by setup, inventory, profile, benchmark, preflight, or safety-soak | Training is expensive and must stay behind explicit commands and a later fine-tune decision. |
| Required cloud voice cloning provider | Saymo remains local-by-default and privacy-preserving. |
| CosyVoice/GPT-SoVITS installation in the first implementation phase | Candidate order requires F5 and Qwen3 score reports before heavier stacks. |
| Production config flip during benchmark generation | Benchmarks are experiments; runtime activation requires explicit profile approval. |
| Using live call recordings as voice-clone training data | Captured calls are reliability fixtures in this milestone, not voice-training material. |
| Fully automatic objective voice scoring as the promotion authority | User-perceived identity and artifacts require blind A/B approval first. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INV-01 | Phase 31 | Complete |
| INV-02 | Phase 31 | Complete |
| INV-03 | Phase 31 | Complete |
| INV-04 | Phase 31 | Complete |
| PROF-01 | Phase 31 | Complete |
| PROF-02 | Phase 31 | Complete |
| PROF-03 | Phase 31 | Complete |
| PROF-04 | Phase 31 | Complete |
| BEN-01 | Phase 32 | Complete |
| BEN-02 | Phase 32 | Complete |
| BEN-03 | Phase 32 | Complete |
| BEN-04 | Phase 32 | Complete |
| BEN-05 | Phase 32 | Complete |
| CAND-01 | Phase 33 | Complete |
| CAND-02 | Phase 33 | Complete |
| CAND-03 | Phase 33 | Complete |
| CAND-04 | Phase 33 | Complete |
| CAND-05 | Phase 33 | Complete |
| RUN-01 | Phase 34 | Complete |
| RUN-02 | Phase 34 | Complete |
| RUN-03 | Phase 34 | Complete |
| RUN-04 | Phase 34 | Complete |
| RUN-05 | Phase 34 | Complete |
| SAFE-01 | Phase 35 | Pending |
| SAFE-02 | Phase 35 | Pending |
| SAFE-03 | Phase 35 | Pending |
| SAFE-04 | Phase 35 | Pending |
| SAFE-05 | Phase 35 | Pending |

**Coverage:**
- v1.8 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-07-07*
*Last updated: 2026-07-07 after completing Phase 34*
