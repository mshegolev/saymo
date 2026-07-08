---
phase: 40-launch-and-realtime-evidence-feedback
type: validation
status: ready_for_planning
created: 2026-07-08
requirements: [EVID-01, EVID-02, EVID-03, EVID-04, EVID-05]
---

# Phase 40 Validation Strategy

## Goal-Backward Truths

Phase 40 is complete only when all of these are true:

1. Launch-readiness artifacts expose sanitized checks, blocker categories,
   cache counts, voice/cache fingerprints, provider status, daemon status,
   mode, artifact paths, and rerun commands without raw meeting content.
2. Realtime evidence can be loaded and summarized from sanitized events for
   launch start/end, cache hits/misses, fallback blocks, provider failures,
   playback attempts, handbrake actions, and stop reasons.
3. Session/rehearsal scorecards include launch health, daemon/control
   availability, cache hit/miss counts, unsafe fallback blocks, provider drift,
   and handbrake/runtime blocker metrics when v1.9 evidence is supplied.
4. Safety-soak fails on unsafe v1.9 evidence: unsafe playback, stale cache,
   missing daemon readiness, provider blockers, or unapproved fallback
   conditions.
5. Troubleshooting output points to sanitized artifact/log paths and exact
   rerun commands, while preserving existing CLI behavior when no new evidence
   is supplied.

## Automated Validation Commands

### Focused Phase 40 Suite

```bash
uv run pytest \
  tests/analysis/test_launch_readiness.py \
  tests/analysis/test_realtime_events.py \
  tests/analysis/test_session_scorecard.py \
  tests/analysis/test_safety_soak.py \
  tests/analysis/test_remediation.py \
  tests/test_call_ready_cli.py \
  tests/test_session_scorecard_cli.py \
  tests/test_safety_soak_cli.py \
  -q
```

### v1.9 Regression Suite

```bash
uv run pytest \
  tests/analysis/test_realtime_gate.py \
  tests/analysis/test_realtime_policy.py \
  tests/analysis/test_realtime_events.py \
  tests/test_auto_qa_flow.py \
  tests/test_call_ready_cli.py \
  tests/test_live_control_cli.py \
  tests/test_realtime_static_guards.py \
  tests/test_call_control_cli.py \
  -q
```

### Safety Regression Suite

```bash
uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q
```

### Full Suite

```bash
uv run pytest
```

### Static Privacy Guard

```bash
! rg "raw_transcript|generated_answer|answer_text|audio_bytes|PRIVATE_" \
  saymo/analysis/launch_readiness.py \
  saymo/analysis/realtime_events.py \
  saymo/analysis/session_scorecard.py \
  saymo/analysis/safety_soak.py \
  saymo/analysis/remediation.py
```

The repository still has legacy trigger-review tests and fixtures that mention
transcripts. Phase 40 guards should stay scoped to launch/realtime/scorecard
evidence modules and must prove new serialized payloads do not include private
meeting content.

### Static Provider/Audio Mutation Guard

```bash
! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" \
  saymo/analysis/launch_readiness.py \
  saymo/analysis/realtime_events.py \
  saymo/analysis/session_scorecard.py \
  saymo/analysis/safety_soak.py \
  saymo/analysis/remediation.py
```

Readiness collection may call non-mutating probe helpers already covered by
Phase 37. Evidence readers and renderers must not add provider/audio mutation
calls.

## Required Test Coverage

### EVID-01: Launch Artifact

- Artifact schema includes checks, blocker counts/categories, cache coverage,
  voice/cache metadata, provider/audio rows, daemon/control rows, mode, and
  rerun commands.
- Artifact JSON and human output omit private sentinels and raw content.
- Existing `call-ready --output` remains backward compatible.

### EVID-02: Realtime Event Evidence

- JSONL loader skips malformed rows and summarizes by outcome/source/label.
- Summary includes cache hit/miss, fallback block, provider block, handbrake
  block, manual route, launch block, playback block, stop/cancel labels when
  present.
- Event payloads and summaries remain sanitized.

### EVID-03: Scorecard Feedback

- Scorecard JSON/Markdown includes launch status, launch blockers, daemon
  readiness, response-cache hit/miss/block counts, provider drift, fallback
  blocks, and handbrake/runtime blocks when evidence is supplied.
- Existing rehearsal/regression scorecard behavior remains compatible when
  launch/realtime evidence is absent.

### EVID-04: Safety-Soak Feedback

- Safety-soak fails for unsafe automatic playback, stale cache evidence,
  missing daemon readiness, provider blockers, and fallback blocks.
- Safe v1.9 evidence passes without regressions.
- Baseline drift behavior remains intact.

### EVID-05: Troubleshooting

- Troubleshooting output includes sanitized failed labels, categories, artifact
  paths, log paths, and exact rerun commands.
- Output includes next actions for call-ready, call-control, scorecard, and
  safety-soak without leaking raw content.

## Manual Verification

After automated tests pass, run locally before trusting live-call diagnostics:

```bash
uv run saymo call-ready -p standup --provider glip --output ~/.saymo/live_control/standup/call-ready.json
uv run saymo auto-preflight -p standup
uv run saymo session-scorecard -p standup --realtime ~/.saymo/live_control/standup/realtime-decisions.jsonl
uv run saymo safety-soak -p standup --scorecard-json <scorecard.json>
```

Expected:

- Artifacts and reports are readable, sanitized, and point to concrete rerun
  commands.
- Unsafe launch/realtime evidence appears in scorecards and fails safety-soak.
- No raw meeting transcript, generated answer text, daily-note body, audio
  bytes, or secrets are present.

## Done Criteria

- Phase 40 focused suite passes.
- v1.9 regression suite passes.
- Safety regression suite passes.
- Full suite passes.
- Static privacy and provider/audio mutation guards pass.
- `40-VERIFICATION.md` marks EVID-01 through EVID-05 verified, or documents any
  non-blocking manual live-call residual risk.
