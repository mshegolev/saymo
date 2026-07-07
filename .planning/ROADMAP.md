# Roadmap: Saymo

## Overview

Milestone v1.8 focuses on Call-ready Voice Clone: making Saymo's cloned voice
safe and reproducible for the real live-call path through local asset
inventory, protected voice profiles, comparable benchmark evidence, explicit
engine/fallback selection, and preview/A-B/safety-soak gates.

## Completed Milestones

- ✅ **v1.7 Live Reliability Rehearsal** - Phases 27-30 shipped 2026-07-07.
  Archives: `.planning/milestones/v1.7-ROADMAP.md`,
  `.planning/milestones/v1.7-REQUIREMENTS.md`,
  `.planning/milestones/v1.7-MILESTONE-AUDIT.md`,
  `.planning/milestones/v1.7-phases/`
- ✅ **v1.6 Live Control Handbrake** - Phases 23-26 shipped 2026-05-22.
  Archives: `.planning/milestones/v1.6-ROADMAP.md`,
  `.planning/milestones/v1.6-REQUIREMENTS.md`,
  `.planning/milestones/v1.6-MILESTONE-AUDIT.md`,
  `.planning/milestones/v1.6-phases/`
- ✅ **v1.5 Live Review + Safe Approved Speak** - Phases 18-22 shipped
  2026-05-21.
- ✅ **v1.4 Live Conversation Memory + Answer Cockpit** - Phases 14-17 shipped
  2026-05-20.
- ✅ **v1.3 Local Diarization Assist** - Phases 11-13 shipped 2026-05-20.
- ✅ **v1.2 Trigger Training Console** - Phases 8-10 shipped 2026-05-20.
- ✅ **v1.1 Call Intelligence Loop** - Phases 5-7 shipped 2026-05-18.
- ✅ **v1.0 Speedly Catcher + Speedly Sayer** - Phases 1-4 shipped
  2026-05-15.

## Active Milestone

- **v1.8 Call-ready Voice Clone** - Phases 31-35 planned.

## Phases

**Phase Numbering:**
- Integer phases (31, 32, 33, 34, 35): Planned milestone work
- Decimal phases (32.1, 32.2): Urgent insertions if needed

- [x] **Phase 31: Voice Asset Inventory and Profile Setup** - Add read-only
  inventory and protected voice profile/reference manifests.
- [x] **Phase 32: Benchmark Scoring and F5 Baseline** - Turn the existing
  shootout harness into scored, comparable F5 baseline evidence.
- [ ] **Phase 33: Candidate Shootout Gates** - Gate Qwen3 Base and later
  challengers behind dry-run, transcript, score-report, and install boundaries.
- [ ] **Phase 34: Call-ready Engine Selector and Fallback Chain** - Wire
  approved engine/fallback resolution into prepare/live synthesis without
  bypassing existing safety paths.
- [ ] **Phase 35: Preview, A/B Approval, and Safety Soak** - Enforce local
  preview, benchmark-backed approval, and voice-readiness safety gates before
  real call use.

## Phase Details

### Phase 31: Voice Asset Inventory and Profile Setup
**Goal**: Let the user understand and protect local voice assets, then create
an explicit voice profile that references existing samples/datasets without
mutating them.
**Depends on**: existing config loader, `train-status`, `test-voice-sample`,
F5/Qwen docs, local `~/.saymo` asset layout
**Requirements**: INV-01, INV-02, INV-03, INV-04, PROF-01, PROF-02, PROF-03,
PROF-04
**Success Criteria** (what must be TRUE):
  1. User can run voice inventory and profile status commands that inspect
     local voice assets without deletion, downloads, training, or metadata
     rewrites.
  2. Inventory reports active engines, model/checkpoint paths, voice samples,
     transcript sidecars, datasets, caches, and benchmark runs with protected
     asset classification.
  3. User can create or update a voice profile in dry-run or explicit apply
     mode, with reference hashes and transcript status.
  4. Profile and inventory exports are sanitized and omit private transcript
     text and secrets.
**Plans**: 4 plans

Plans:
- [ ] 31-01: Add voice inventory contracts and read-only scanner
- [ ] 31-02: Add voice profile manifest model and atomic writer
- [ ] 31-03: Add CLI commands for inventory, profile init/status, and reference checks
- [ ] 31-04: Add docs and tests proving protected assets are not mutated

### Phase 32: Benchmark Scoring and F5 Baseline
**Goal**: Produce comparable, scored F5 baseline evidence before evaluating or
promoting any challenger engine.
**Depends on**: Phase 31 profile/reference contracts,
`scripts/voice_clone_benchmark.py`, docs/voice-clone-shootout.md
**Requirements**: BEN-01, BEN-02, BEN-03, BEN-04, BEN-05
**Success Criteria** (what must be TRUE):
  1. F5 dry-run, smoke, and full benchmark runs use the same phrase ids,
     reference metadata, manifest schema, and transcript-redaction rules.
  2. Each benchmark run writes or updates WAV clips, `manifest.json`,
     `blind-review.md`, `review.json`, and `score-report.md`.
  3. User can enter blind-review scores and produce a report that marks the
     run dry-run, partial, complete, rejected, or approved.
  4. F5 baseline score evidence is required before challenger promotion gates
     can pass.
**Plans**: 4 plans

Plans:
- [ ] 32-01: Extract benchmark artifact contracts and preserve script compatibility
- [ ] 32-02: Add review scoring and `score-report.md` generation
- [ ] 32-03: Add F5 baseline gate and transcript-redaction tests
- [ ] 32-04: Update shootout docs with baseline and scoring workflow

### Phase 33: Candidate Shootout Gates
**Goal**: Evaluate Qwen3 Base and later candidates without accidental installs,
downloads, runtime promotion, or training.
**Depends on**: Phase 32 score reports, existing Qwen3 Base dry-run path,
internal Nexus PyPI install convention
**Requirements**: CAND-01, CAND-02, CAND-03, CAND-04, CAND-05
**Success Criteria** (what must be TRUE):
  1. Qwen3 Base dry-run still produces benchmark-shaped artifacts without
     importing `qwen_tts` or downloading model files.
  2. Real Qwen3 Base benchmark fails fast without reference transcript and
     records official Base-vs-runtime separation in artifacts and docs.
  3. CosyVoice, GPT-SoVITS, and LoRA training remain blocked unless prior
     score reports explicitly justify opening the next gate.
  4. Approved package installs are documented as isolated-runtime commands,
     preferring internal Nexus3 PyPI where applicable, without committed
     package-index hardcoding.
**Plans**: 4 plans

Plans:
- [ ] 33-01: Harden Qwen3 Base dry-run and real-run prerequisite gates
- [ ] 33-02: Add candidate-gate checks against baseline and Qwen score reports
- [ ] 33-03: Document isolated runtime install flow with internal PyPI preference
- [ ] 33-04: Add tests/docs separating Qwen3 Base benchmark from `qwen3_clone`

### Phase 34: Call-ready Engine Selector and Fallback Chain
**Goal**: Let runtime synthesis use only approved voice profile engines and
explicit fallbacks while preserving existing prepare, cache, handbrake, and
provider safety behavior.
**Depends on**: Phases 31-33, TTS factory, response cache, prepare/speak/auto
paths
**Requirements**: RUN-01, RUN-02, RUN-03, RUN-04, RUN-05
**Success Criteria** (what must be TRUE):
  1. User can configure purpose-specific approved engine/fallback chains for
     preview, prepare, response cache, realtime, and approved live call.
  2. Synthesis goes through one selector that constructs engines through the
     existing factory and records selected/fallback metadata.
  3. Prepared audio and response-cache entries carry voice profile, reference,
     engine, fallback, and selector fingerprints.
  4. Live-call paths fail closed on missing approval, stale cache, or
     non-cloned fallback unless that fallback is explicitly approved.
**Plans**: 5 plans

Plans:
- [ ] 34-01: Add selector config and engine/fallback resolution contracts
- [ ] 34-02: Route prepare and response-cache synthesis through the selector
- [ ] 34-03: Route approved live synthesis through readiness and selector checks
- [ ] 34-04: Add cache voice-fingerprint metadata and stale-cache blockers
- [ ] 34-05: Add fallback audit metadata and non-cloned fallback safeguards

### Phase 35: Preview, A/B Approval, and Safety Soak
**Goal**: Prove that cloned voice output is previewed, approved, and covered by
the same pre-call safety gates before it reaches a real call.
**Depends on**: Phases 31-34, rehearsal, session-scorecard, safety-soak,
answer cockpit approval gates
**Requirements**: SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05
**Success Criteria** (what must be TRUE):
  1. User can preview cloned voice locally or to the monitor route without
     sending unapproved audio to BlackHole/provider call output.
  2. User can approve or reject a voice profile/engine by linking score
     evidence and recording gate pass, rejection, or explicit override.
  3. Real call output is blocked when profile approval, benchmark evidence,
     reference fingerprint, cache fingerprint, or fallback consent is missing
     or stale.
  4. Auto-preflight, rehearsal, scorecard, and safety-soak report voice
     readiness and fail on unapproved/stale/fallback hazards.
**Plans**: 5 plans

Plans:
- [ ] 35-01: Add preview command/path and monitor-route audit metadata
- [ ] 35-02: Add A/B approval artifacts and profile approval commands
- [ ] 35-03: Block real call output on missing or stale voice approval
- [ ] 35-04: Extend preflight, rehearsal, and scorecard with voice readiness
- [ ] 35-05: Extend safety-soak with voice readiness failure invariants

## Progress

**Execution Order:**
Phases execute in numeric order: 31 -> 32 -> 33 -> 34 -> 35

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 31. Voice Asset Inventory and Profile Setup | v1.8 | 4/4 | Complete | 2026-07-07 |
| 32. Benchmark Scoring and F5 Baseline | v1.8 | 4/4 | Complete | 2026-07-07 |
| 33. Candidate Shootout Gates | v1.8 | 0/4 | Pending | — |
| 34. Call-ready Engine Selector and Fallback Chain | v1.8 | 0/5 | Pending | — |
| 35. Preview, A/B Approval, and Safety Soak | v1.8 | 0/5 | Pending | — |

## Requirement Coverage

| Requirement | Phase |
|-------------|-------|
| INV-01 | Phase 31 |
| INV-02 | Phase 31 |
| INV-03 | Phase 31 |
| INV-04 | Phase 31 |
| PROF-01 | Phase 31 |
| PROF-02 | Phase 31 |
| PROF-03 | Phase 31 |
| PROF-04 | Phase 31 |
| BEN-01 | Phase 32 |
| BEN-02 | Phase 32 |
| BEN-03 | Phase 32 |
| BEN-04 | Phase 32 |
| BEN-05 | Phase 32 |
| CAND-01 | Phase 33 |
| CAND-02 | Phase 33 |
| CAND-03 | Phase 33 |
| CAND-04 | Phase 33 |
| CAND-05 | Phase 33 |
| RUN-01 | Phase 34 |
| RUN-02 | Phase 34 |
| RUN-03 | Phase 34 |
| RUN-04 | Phase 34 |
| RUN-05 | Phase 34 |
| SAFE-01 | Phase 35 |
| SAFE-02 | Phase 35 |
| SAFE-03 | Phase 35 |
| SAFE-04 | Phase 35 |
| SAFE-05 | Phase 35 |

**Coverage:** 28/28 requirements mapped.
