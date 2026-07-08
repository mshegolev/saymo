# Requirements: Saymo v1.9 Call Launch Readiness

**Defined:** 2026-07-08
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.9 Requirements

Requirements for milestone v1.9 Call Launch Readiness.

### Call-Ready Launch Gate

- [x] **LAUN-01**: User can run one call-ready command for a profile and
  provider that returns a concise `ready` or `not ready` result before a call.
- [x] **LAUN-02**: User can have the call-ready flow create or verify today's
  Obsidian daily note without overwriting existing note content.
- [x] **LAUN-03**: User can see daily-note source readiness separately from
  file existence, including a blocker when the note contains only placeholders
  or no usable standup content.
- [x] **LAUN-04**: User can have the call-ready flow prepare or verify the
  current standup audio for the selected profile without silently accepting
  stale prepared WAVs.
- [x] **LAUN-05**: User can see response-cache coverage for the selected
  profile, voice, and response library as counts plus exact stale or missing
  variant blockers.
- [x] **LAUN-06**: User can see approved cloned-voice metadata for prepared
  and response-cache audio, including selected engine, voice profile,
  approval state, reference fingerprint, and stale-cache reason.
- [x] **LAUN-07**: User can get grouped `block`, `warn`, and `info`
  remediation with exact action and rerun commands for every call-ready check.

### Provider and Audio Readiness

- [x] **PROV-01**: User can verify the configured provider and Chrome meeting
  tab are present, identifiable, and actionable before starting realtime mode.
- [x] **PROV-02**: User can verify BlackHole capture/playback routing and the
  real microphone takeover route before joining or starting the live loop.
- [x] **PROV-03**: User can see provider capability details such as tab
  activation, mic switching support, mute recovery, and unsupported provider
  limitations without parsing raw errors.
- [x] **PROV-04**: User can see macOS permission blockers for hotkeys,
  microphone capture, Chrome automation, and audio routing with targeted
  remediation.
- [x] **PROV-05**: User can run provider/audio readiness without destructive
  provider actions such as killing Chrome, leaving a meeting, or changing
  system routes unless an explicit command requests it.

### Local Control Daemon

- [x] **CTRL-01**: User can install, start, stop, restart, and inspect a
  per-profile Saymo call-control LaunchAgent from CLI commands.
- [x] **CTRL-02**: User can run a foreground call-control daemon that
  registers configured global hotkeys and publishes a fresh heartbeat/status
  for the selected profile.
- [x] **CTRL-03**: User can see whether the call-control daemon is installed,
  loaded, running, stale, crash-looping, missing permissions, or using an
  outdated LaunchAgent plist.
- [x] **CTRL-04**: User can queue the existing live-control actions from the
  daemon or status surface with the same semantics and audit trail as CLI and
  current hotkeys.
- [x] **CTRL-05**: User can prove the handbrake is reachable before realtime
  mode by checking heartbeat freshness, hotkey registration, command write,
  command consumption, and latest applied action evidence.

### Realtime Meeting Loop

- [x] **REAL-01**: User can start realtime mode only after the selected
  launch-readiness level passes for the profile, provider, cloned voice,
  cache, handbrake, and audio route.
- [x] **REAL-02**: User can preserve the existing `saymo auto` workflow while
  using the same shared launch-readiness gate as any new call-start or
  realtime alias.
- [x] **REAL-03**: User can rely on automatic question handling to fail closed
  on response-cache miss, stale voice metadata, unsafe fallback, provider loss,
  manual takeover, hard-disable, or disabled auto-answer.
- [x] **REAL-04**: User can still trigger explicit prepared standup playback as
  a manual action when allowed, without that manual path becoming automatic
  cache-miss fallback.
- [x] **REAL-05**: User can see why each realtime decision spoke, skipped, or
  blocked using sanitized route names such as response-cache hit,
  cache-miss-blocked, handbrake-blocked, provider-blocked, or fallback-blocked.
- [x] **REAL-06**: User can keep deterministic addressing and existing
  handbrake state as the live-call safety boundary; classifiers or LLM wording
  cannot override a deterministic skip in this milestone.

### Launch and Realtime Evidence

- [x] **EVID-01**: User can inspect a sanitized launch-readiness artifact that
  records checks, blocker categories, cache counts, voice/cache fingerprints,
  provider status, daemon status, mode, and rerun commands without raw meeting
  content.
- [x] **EVID-02**: User can inspect sanitized realtime events for launch
  start/end, cache hits/misses, fallback blocks, provider failures, playback
  attempts, handbrake actions, and stop reasons.
- [x] **EVID-03**: User can see launch health, daemon/control availability,
  cache hit/miss counts, unsafe fallback blocks, and provider drift in
  rehearsal or session scorecards.
- [x] **EVID-04**: User can run safety-soak against v1.9 launch and realtime
  evidence, and the gate fails on unsafe playback, stale cache, missing daemon
  readiness, provider blockers, or unapproved fallback conditions.
- [ ] **EVID-05**: User can troubleshoot launch and realtime failures from
  sanitized evidence that includes log/artifact paths and next rerun commands.

## Future Requirements

Deferred beyond v1.9.

### Native UI and Scheduling

- User can manage Saymo from a polished native macOS menu bar app with
  settings, history, and answer-cockpit integration after the daemon/control
  contract is stable.
- User can launch call readiness from calendar events or meeting URLs after the
  manual call-ready workflow is trusted.
- User can use voice commands as an additional handbrake path after hotkeys and
  daemon controls prove reliable.

### Advanced Realtime Behavior

- User can opt into guarded live LLM+TTS fallback after latency, quality,
  source-grounding, approval, and failure-mode evidence justify it.
- User can let Saymo perform limited provider auto-repair after non-destructive
  remediation commands and provider-specific tests prove safety.
- User can use richer realtime classifier assistance after deterministic
  addressing and saved-session regressions remain the safety boundary.

### Voice and Model Work

- User can retrain or replace voice models after explicit dataset, runtime,
  and cleanup gates are added in a separate milestone.
- User can benchmark heavier candidate engines only after v1.8 score evidence
  and isolated install plans justify the cost.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full native menu bar application packaging | v1.9 needs a daemon/status/control contract first; polished UI can follow later. |
| Calendar-based automatic launch | Manual call-ready must prove reliable before unattended scheduling. |
| Live LLM+TTS fallback for automatic answers | Cache misses must fail closed until latency, approval, and voice-quality gates exist. |
| Automatic provider repair that changes live app state | Pre-call remediation should be explicit; killing Chrome or changing call state can disrupt meetings. |
| Voice model training, downloads, or cleanup from call-ready | Voice assets are protected and expensive; training/cleanup stays behind explicit commands. |
| Using live call recordings as voice-training data | Call recordings remain reliability fixtures, not voice identity training data. |
| Cloud voice or meeting control as a required path | Saymo remains local-by-default. |
| Full autonomous meeting participation | The product remains an assistant with manual takeover and explicit safety boundaries. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LAUN-01 | Phase 36 | Complete |
| LAUN-02 | Phase 36 | Complete |
| LAUN-03 | Phase 36 | Complete |
| LAUN-04 | Phase 36 | Complete |
| LAUN-05 | Phase 36 | Complete |
| LAUN-06 | Phase 36 | Complete |
| LAUN-07 | Phase 36 | Complete |
| PROV-01 | Phase 37 | Complete |
| PROV-02 | Phase 37 | Complete |
| PROV-03 | Phase 37 | Complete |
| PROV-04 | Phase 37 | Complete |
| PROV-05 | Phase 37 | Complete |
| CTRL-01 | Phase 38 | Complete |
| CTRL-02 | Phase 38 | Complete |
| CTRL-03 | Phase 38 | Complete |
| CTRL-04 | Phase 38 | Complete |
| CTRL-05 | Phase 38 | Complete |
| REAL-01 | Phase 39 | Complete |
| REAL-02 | Phase 39 | Complete |
| REAL-03 | Phase 39 | Complete |
| REAL-04 | Phase 39 | Complete |
| REAL-05 | Phase 39 | Complete |
| REAL-06 | Phase 39 | Complete |
| EVID-01 | Phase 40 | Complete |
| EVID-02 | Phase 40 | Complete |
| EVID-03 | Phase 40 | Complete |
| EVID-04 | Phase 40 | Complete |
| EVID-05 | Phase 40 | Pending |

**Coverage:**
- v1.9 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-07-08*
*Last updated: 2026-07-08 after creating v1.9 roadmap*
