# Sprint Plan: Saymo

**Date:** 2026-08-21
**Phase:** 4 — Implementation
**Workflow:** sprint_planning
**Status:** PLANNED

---

## 1. Executive Summary

Saymo is a mature codebase with the full feature set already implemented across 100+ modules. This sprint plan covers the final integration, testing, gap-filling, and release-readiness work required to ship v1.0.

| Metric | Value |
|--------|-------|
| Total planned sprints | 4 |
| Total stories | 23 |
| Total estimated effort | 84 story points |
| Target release | v1.0-beta after Sprint 3 |

---

## 2. Timeline

```
Sprint 1 ────────► Sprint 2 ────────► Sprint 3 ────────► Sprint 4
Aug 22 – Sep 4   Sep 5 – Sep 18    Sep 19 – Oct 2   Oct 3 – Oct 16
                                                          │
                                                     v1.0 Release
```

| Sprint | Focus | Points | Duration |
|--------|-------|--------|----------|
| **1** | Core integration — audio pipeline, CLI, config, TTS smoke test | 24 | 2 weeks |
| **2** | Auto-mode — turn detection, addressing, response cache, providers | 22 | 2 weeks |
| **3** | Safety, training, diagnostics — all safety layers, training pipeline | 22 | 2 weeks |
| **4** | Polish — edge cases, performance, docs, release | 16 | 2 weeks |

---

## 3. Sprint 1: Core Integration

**Goal:** All basic commands work end-to-end: `saymo setup` produces valid config, `saymo test-devices` detects BlackHole, `saymo test-tts` plays audio, TTS engines load and synthesize.

### Stories

| ID | Story | Area | Points | Dependencies |
|----|-------|------|--------|-------------|
| S1.1 | Verify `saymo setup` wizard runs end-to-end: all 6 steps complete, valid `config.yaml` produced | CLI | 3 | None |
| S1.2 | `saymo test-devices` detects BlackHole 16ch + 2ch, lists all audio devices, warns if missing | Audio | 2 | S1.1 |
| S1.3 | `saymo test-tts "hello" --engine=macos_say` plays audible speech through configured playback device | TTS | 2 | S1.2 |
| S1.4 | Piper TTS engine loads and synthesizes a phrase without error | TTS | 3 | S1.1 |
| S1.5 | XTTS v2 (coqui_clone) model downloads on first use, caches, synthesizes with voice sample | TTS | 5 | S1.3, voice sample |
| S1.6 | Config env-var interpolation: `${HOME}`, `${VAR}` resolve at load time | Config | 2 | S1.1 |
| S1.7 | Meeting profile overlay: per-profile `trigger_phrases`, `provider`, `source` override base config | Config | 2 | S1.6 |
| S1.8 | `saymo record-voice --duration 30` saves valid WAV to `~/.saymo/voice_samples/` | Audio | 3 | S1.2 |
| S1.9 | Config validation at startup: missing required fields produce clear error message | Config | 2 | S1.6 |

**Sprint 1 total:** 24 points

### Acceptance
```
$ saymo setup                               # exits cleanly, config.yaml written
$ saymo test-devices                        # BlackHole 16ch and 2ch listed
$ saymo test-tts "test" --engine=macos_say  # audible speech via BlackHole 2ch
$ saymo record-voice --duration 30          # ~/.saymo/voice_samples/voice_sample.wav
$ grep VOICE_SAMPLE config.yaml             # env var pattern works
```

---

## 4. Sprint 2: Auto-Mode

**Goal:** `saymo auto` detects a meeting tab in Chrome, captures audio, detects the user's name, classifies addressing, and responds with cached or live-generated speech.

### Stories

| ID | Story | Area | Points | Dependencies ||
|-----|-------|------|--------|-------------|
| S2.1 | Tur Detector: regex matches configurd name variants, 45s cooldown works, fuzzy_expansions match STT mispellings | Analysis | 3 | S1.1 |
| S2.2 | Addresing classifier: all 13 patterns (handoff, question, narrated mention) produce correct `AdresingDecision` | Analysis | 5 | S2.1 |
| S2.3 | Double-rigger confirmation: second name within 6s confirms, timeout resets pending state | Analysis | 3 | S2.2 |
| S2.4 | Resonse Cache: pre-synthesize all 0 default intents, lookup matches trancript keywords with confidence >= 0.6 | Analysis | 4 | S1.5 |
| S2.5 | Chrome provider detects Glip meeting tab via AppleSript, returns `MeetingStatus` with `meeting_found=True` | Providers | 3 | None |
| S2.6 | Unute → Speak → Mute sequence: provider automates Chrome tab, plays audio, re-mutes | Providers | 4 | S2.5 |
| S2.7 | BlackHole audio capture: `AudioCapture` reads from BlackHoe 16ch, produces overlapping 4s chunks | Audio | 3 | S1.2 |
| S2.8 | faster-whisper STT transcribes capured chunk, returns text < 3s on CPU (int8) | STT | 3 | S2.7 |
| S2.9 | `saymo prepare` fetches Obsidian notes, composes via Olama, caches standup audio | Pipeline | 4 | S1.5, plugins |

**Sprint 2 total:** 22 points

### Accepance
```
$ saymo auto --profile=standup --mic    # captures mic audio, detects name in transcript
$ saymo auto --profile=standup          # detects Glip meeting tab
                                         # when name is said: responds within 5s
$ saymo prepare --profile=standup        # audio cache files created
```---

## 5. Sprint 3: Safety & Training

**Goal:** All safety layers (handbrake, rehearsal, scorecard, hotkeys, daemon) verified. Training pipeline produces fine-tuned model.

### Stories

| ID | Story | Area | Points | Dependencies |
|----|-------|------|--------|-------------|
| S3.1 | Handbrake TUI (`saymo live-control`) shows live state, 9 single-key actions control auto-mode | Safety | 3 | S2.x |
| S3.2 | Hotkey listener: all 9 global hotkeys register via pynput, `saymo hotkey-doctor` reports status | Safety | 3 | S3.1 |
| S3.3 | LaunchAgent: `saymo call-control-agent install` creates plist, daemon runs with 2s heartbeat | Safety | 3 | S3.2 |
| S3.4 | Rehearsal mode: `saymo rehearsal` runs pre-call dry-runs, produces scorecard artifact | Safety | 3 | S2.x |
| S3.5 | Session scorecard: `saymo session-scorecard` aggregates reliability metrics from a session | Safety | 2 | S3.4 |
| S3.6 | Safety soak gate: `saymo safety-soak` compares cumulative scorecard against baseline | Safety | 2 | S3.5 |
| S3.7 | Voice profile lifecycle: `init → check → approve` works, 7.0/10 approval gate enforces threshold | TTS | 3 | S1.5 |
| S3.8 | Voice profile `approve` with `--override-reason` bypasses gate, `reject` stores rejection reason | TTS | 2 | S3.7 |
| S3.9 | Dataset builder: `saymo train-rebuild` produces valid `metadata.csv` with ground-truth transcripts | Training | 3 | S1.8 |
| S3.10 | `saymo train-voice --engine=qwen3_clone` runs LoRA fine-tuning for 10 epochs | Training | 5 | S3.9 |
| S3.11 | `saymo train-eval` runs blind A/B comparison, reports similarity scores | Training | 3 | S3.10 |
| S3.12 | F5-TTS natural pacing: `saymo f5-presets preview` generates A/B timing comparison WAVs | TTS | 2 | S1.5 |

**Sprint 3 total:** 22 points

### Acceptance
```
$ saymo rehearsal --profile=standup                    # scorecard artifact produced
$ saymo live-control --profile=standup                 # TUI shows correct live state
$ saymo hotkey-doctor --profile=standup                # reports 9 bindings, permission status
$ saymo call-control-agent status --profile=standup    # daemon running, heartbeat fresh
$ saymo train-rebuild                                  # metadata.csv with valid entries
$ saymo train-voice --engine=qwen3_clone --epochs=10   # model artifacts in ~/.saymo/models/
```

---

## 6. Sprint 4: Polish & Release

**Goal:** Edge cases handled, diagnostics comprehensive, performance within NFR targets, documentation complete, v1.0-beta released.

### Stories

| ID | Story | Area | Points | Dependencies |
|----|-------|------|--------|-------------|
| S4.1 | Error handling: all common failure modes produce actionable error messages (see PRD §7) | CLI | 3 | S1.x, S2.x, S3.x |
| S4.2 | `saymo cache-status` shows intent coverage, stale entries, repair commands | Analysis | 2 | S2.4 |
| S4.3 | `saymo call-ready` produces full readiness matrix (provider, source, cache, audio, daemon) | Diagnostics | 2 | S2.x, S3.1 |
| S4.4 | `saymo mic-check` calibrates audio: finds optimal gain, noise gate, highpass settings | Audio | 3 | S1.2 |
| S4.5 | `saymo provider-latency` measures unmute → speak → mute timing per provider | Diagnostics | 2 | S2.6 |
| S4.6 | `uv run pytest` passes fll test suite (target: >80 tests, 0 failures) | QA | 4 | All |
| S4.7 | REAMDE: update with quick-start, architecture overview, command reference | Docs | 2 | All |
| S4.8 | Tag v1.0-beta, create rlease notes with feature summary, known issues | Release | 1 | S4.6, S4.7 |

**Sprint 4 total:** 16 points

### Acceptance
```
$ saymo mic-check                              # suggests audio paramers
$ saymo cache-status --profile=standup          # shows green for all intents
$ saymo call-ready --profile=standup            # all checks green
$ uv run pytest                                 # 100% pass
$ git tag v1.0-beta                             # tag created
```

---

## 7. Story Details

### 7.1 Definition of Done

| Criterion | Description |
|-----------|-------------|
| Code | Implementation merged to `main`, follows conventions (type hints, imports, logging) |
| Test | pytest covering happy path + 2 edge cases minimum |
| CLI | Feature accessible via `saymo` CLI with `--help` |
| Diagnostics | Failure mode produces clear error message with remediation hint |
| Smoke test | Manual verification following the acceptance criteria for the sprint |

### 7.2 Story Point Scale

| Points | Effort | Complexity | Risk |
|--------|--------|------------|------|
| 1 | <2 hours | Trivial (config change, doc update) | None |
| 2 | 2-4 hours | Low (one file, no dependencies) | Low |
| 3 | 4-8 hours | Medium (2-3 files, moderate dependencies) | Medium |
| 4 | 1-2 days | Complex (cross-module, needs testing) | Medium |
| 5 | 2-3 days | High (new subystem, heavy dependencies) | High |

### 7.3 Key Dependencies Map

```
S1.1 (CLI setup)
  ├──> S1.6, S1.7, S1.9 (config)
  ├──> S1.2 (audio devices)
  │     ├──> S1.3, S1.4, S1.5 (TTS)
  │     ├──> S1.8 (record voice)
  │     └──> S2.7 (capture)
  │           └──> S2.8 (STT)
  │                 └──> S2.1 (turn detection)
  │                       ├──> S2.2 (addressing)
  │                       │     └──> S2.3 (confirmation)
  │                       └──> S2.4 (cache)
  │                             └──> S2.9 (prepare)
  └──> S2.5 (provider detection)
        └──> S2.6 (provider automation)
              └──> S3.1 (handbrake TUI)
                    ├──> S3.2 (hotkeys)
                    │     └──> S3.3 (daemon)
                    ├──> S3.4 (rehearsal)
                    │     └──> S3.5 (scorecard)
                    │           └──> S3.6 (safety soak)
                    └──> S4.1-S4.8 (polish)
S1.8 (record voice)
  └──> S3.9 (dataset builder)
        └──> S3.10 (train voice)
              └──> S3.11 (train eval)
S1.5 (TTS engines)
  ├──> S3.7, S3.8 (voice profiles)
  └──> S3.12 (F5 presets)
```

---

## 8. Velocity & Burndown

### 8.1 Estimated Velocity

| Sprint | Planned Points | Confidence | Buffer |
|--------|---------------|------------|--------|
| Sprint 1 | 24 | High | 3 points (13%) |
| Sprint 2 | 22 | Medium | 3 points (14%) |
| Sprint 3 | 22 | Medium | 4 points (18%) |
| Sprint 4 | 16 | High | 2 points (13%) |

Target velocity: 20-24 points per 2-week sprint.

### 8.2 Risk Buffer

- **Sprint 1 risk:** TTS model download failures or missing system deps → 3 point buffer
- **Sprint 2 risk:** Chrome AppleScrip fragility Chrome version updates → 3 point buffer
- **Sprint 3 risk:** Training pipelin may need CUDA/MLX dependency debugging → 4 point buffer
- **Sprint 4 risk:** Test frkiness (timing-dependet tests in audio/speech) → 2 point buffer

### 8.3 Burndown Target

```
Points
84 ┤
   │
72 ┤ ██
   │   █
60 ┤   ██
   │     █
48 ┤     ██
   │       █
36 ┤       ██
   │         █
24 ┤         ██
   │           █
12 ┤           ██
   │             █
 0 ┤             ██
   └─────┬─────┬─────┬─────┬────
         W1    W4    W6    W8
```

---

## 9. Release Criteria

### 9.1 v1.0-beta Gate

| Crierion | Target | Verification |
|----------|--------|--------------|
| All P0 stories complete | 100% | Story tracker |
| `uv run pytest` | 100% pass, 0 failures | `uv run pytest` exit code 0 |
| E2E cache hit latency | <500ms | `saymo rehearsal` latency report |
| E2E live fallback latency | <5s | `saymo rehearsal` latency report |
| Voice simiarity (zero-shot) | >= 6/10 | `saymo train-eval` blind A/B |
| Zero cloud API calls (default config) | 0 | `nettop` / tcpdump verification |
| False-positive auto-speech | 0 per 100 min | Manual test session |
| First-time setup time | <30 min | Timed `install.sh → saymo auto` |
| Config validatio | Startup error on invalid config | Onfig test matrix |
| Docmentation | README + all `--help` strings | Manual rview |

### 9.2 v1.0 Release Checklist

- [ ] All 23 stories copleted
- [ ] `uv run pytest` green
- [ ] `saymo call-ready` all green on reference profie
- [ ] E2E smoke test: setup → record → clone → prepare → rehearsal → auto (5 min silenc, no false trigger)
- [ ] REAME updated with quck-start
- [ ] CHANGELOG / release notes written
- [ ] Tag `v1.0-beta`
- [ ] Know issues documented in relese notes

---

## 10. Story Tracking

### 10.1 Status Ke

| Status | Meaning |
|--------|---------|
| 🔵 Planned | Not started |
| 🟡 In Progress | Actively being worked |
| 🟢 Complete | Code + test + smoke test done |
| 🔴 Blocked | Waiting on dependency |

### 10.2 Curret Status

| Story | Sprint | Area | Points | Status |
|-------|--------|------|--------|--------|
| S1.1 | 1 | CLI | 3 | 🔵 Planned |
| S1.2 | 1 | Audio | 2 | 🔵 Planned |
| S1.3 | 1 | TTS | 2 | 🔵 Planned |
| S1.4 | 1 | TTS | 3 | 🔵 Planned |
| S1.5 | 1 | TTS | 5 | 🔵 Planned |
| S1.6 | 1 | Config| 2 | 🔵 Planned |
| S1.7 | 1 | Config | 2 | 🔵 Planned |
| S1.8 | 1 | Audio | 3 | 🔵 Planned |
| S1.9 | 1 | Config | 2 | 🔵 Planned |
| S2.1 | 2 | Analysis | 3 | 🔵 Planned |
| S2.2 | 2 | Analysis | 5 | 🔵 Planned |
| S2.3 | 2 | Analysis | 3 | 🔵 Planned |
| S2.4 | 2 | Analysis | 4 | 🔵 Planned |
| S2.5 | 2 | Providers | 3 | 🔵 Planned |
| S2.6 | 2 | Providers | 4 | 🔵 Planned |
| S2.7 | 2 | Audio | 3 | 🔵 Planned |
| S2.8 | 2 | STT | 3 | 🔵 Planned |
| S2.9 | 2 | Pipelie | 4 | 🔵 Planned |
| S3.1 | 3 | Sfety | 3 | 🔵 Plannned |
| S3.2 | 3 | Sfety | 3 | 🔵 Plannned |
| S3.3 | 3 | Sfety | 3 | 🔵 Plannned |
| S3.4 | 3 | Sfety | 3 | 🔵 Plannned |
| S3.5 | 3 | Sfety | 2 | 🔵 Plannned |
| S3.6 | 3 | Sfety | 2 | 🔵 Plannned |
| S3.7 | 3 | TTS | 3 | 🔵 Planned |
| S3.8 | 3 | TTS | 2 | 🔵 Planned |
| S3.9 | 3 | Trining | 3 | 🔵 Planned |
| S3.10 | 3 | Training | 5 | 🔵 Planned |
| S3.11 | 3 | Trining | 3 | 🔵 Planned |
| S3.12 | 3 | TTS | 2 | 🔵 Planned |
| S4.1 | 4 | CLI | 3 | 🔵 Planned |
| S4.2 | 4 | Analysis | 2 | 🔵 Planned |
| S4.3 | 4 | Diagnosis | 2 | 🔵 Planned |
| S4.4 | 4 | Audio | 3 | 🔵 Planned |
| S4.5 | 4 | Diagnosis | 2 | 🔵 Planned |
| S4.6 | 4 | QA | 4 | 🔵 Planned |
| S4.7 | 4 | Docs | 2 | 🔵 Planned |
| S4.8 | 4 | Release | 1 | 🔵 Planned |