# Requirements: Saymo v1.14 Call Dry-Run To Real Call

**Goal:** Make Saymo reliably prepare, validate, and prove a real standup
launch path through one operator dry-run flow before starting `saymo auto`.

## Requirements

### Dry-Run Flow

- [ ] **DRY-01**: User can run one profile/provider dry-run command that
  verifies whether Saymo is ready for the next real standup without starting
  realtime mode.
- [ ] **DRY-02**: User can see one concise `ready` or `not ready` result with
  grouped blockers, warnings, exact actions, and rerun commands.
- [ ] **DRY-03**: User can run the dry-run without synthesizing audio, playing
  audio, deleting cache artifacts, retraining, downloading voice models, or
  mutating protected `.saymo` assets automatically.

### Source Data And Prepared Audio

- [ ] **SRC-01**: User can have the dry-run verify or create the selected
  Obsidian daily note for the active profile without overwriting existing note
  content.
- [ ] **SRC-02**: User can see whether prepared standup audio matches the
  selected daily-note/source hash, voice profile, and F5 source-type preset
  metadata.
- [ ] **SRC-03**: User can get targeted repair commands for missing or stale
  prepared audio, including `saymo prepare -p <profile>` and review guidance
  when needed.

### Cache And Voice Readiness

- [ ] **CACHE-01**: User can see response-cache coverage and staleness for the
  active profile using source-aware F5 `response_cache` metadata.
- [ ] **CACHE-02**: User can get targeted response-cache repair guidance such
  as `saymo prepare-responses -p <profile>` without automatic rebuilds or
  `--force` by default.
- [ ] **VOICE-01**: User can verify approved cloned-voice profile readiness and
  stale voice metadata before launch without touching voice training data or
  model checkpoints.

### Provider, Audio, And Control Health

- [ ] **ENV-01**: User can verify provider tab readiness, Chrome/provider
  state, BlackHole capture/playback devices, and audio routing prerequisites in
  one dry-run result.
- [ ] **ENV-02**: User can verify call-control daemon and LaunchAgent health,
  including heartbeat freshness, hotkey availability, stale plist status, and
  exact restart/probe commands.
- [ ] **ENV-03**: User can keep provider repair explicit: dry-run diagnostics
  may suggest safe commands but must not kill apps, change meeting state, or
  switch devices automatically.

### Evidence And Rehearsal

- [ ] **EVID-01**: User can save a sanitized dry-run artifact with profile,
  provider, check statuses, stale reasons, actions, rerun commands, and
  timestamps without raw meeting text, prompt text, response text, audio bytes,
  secrets, voice samples, or training data.
- [ ] **EVID-02**: User can feed dry-run evidence into rehearsal, session
  scorecard, and safety-soak so the next real call has a repeatable
  launch-readiness signal.
- [ ] **EVID-03**: User can compare the latest dry-run result with the previous
  result to see whether readiness improved or regressed before joining a call.

## Future Requirements

- Live Answer Policy: confidence gates, manual approval mode, skip/takeover
  telemetry, and name-mention safety.
- Voice Naturalness Feedback Loop: store preference-review outcomes and
  recommend candidate presets without auto-apply.
- Meeting Memory Quality: source priority, stale source warnings, and answer
  citations.
- Calendar/meeting URL launch: automatic call readiness from calendar after the
  manual flow is trusted.
- Limited provider auto-repair after explicit operator approval.

## Out of Scope

- Starting `saymo auto` automatically from dry-run. The operator starts
  realtime explicitly after readiness passes.
- Automatic provider repair that changes live app, browser, or call state. That
  can disrupt meetings.
- Voice retraining, model downloads, model cleanup, or checkpoint deletion.
  Protected local voice assets stay behind explicit commands.
- Automatic prepared/response cache rebuilds or `--force` regeneration. Repairs
  stay explicit and targeted.
- Changing answer policy or confidence gates. That belongs to v1.15.
- Cloud services or remote voice processing. Saymo remains local-by-default.
- Calendar-based unattended launch. Defer until manual dry-run is trusted.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DRY-01 | Phase 48 | Pending |
| DRY-02 | Phase 48 | Pending |
| DRY-03 | Phase 48 | Pending |
| SRC-01 | Phase 49 | Pending |
| SRC-02 | Phase 49 | Pending |
| SRC-03 | Phase 49 | Pending |
| CACHE-01 | Phase 49 | Pending |
| CACHE-02 | Phase 49 | Pending |
| VOICE-01 | Phase 49 | Pending |
| ENV-01 | Phase 50 | Pending |
| ENV-02 | Phase 50 | Pending |
| ENV-03 | Phase 50 | Pending |
| EVID-01 | Phase 51 | Pending |
| EVID-02 | Phase 51 | Pending |
| EVID-03 | Phase 51 | Pending |
