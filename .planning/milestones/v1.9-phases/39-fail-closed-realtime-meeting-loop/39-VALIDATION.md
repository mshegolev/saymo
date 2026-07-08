---
phase: 39-fail-closed-realtime-meeting-loop
type: validation
status: ready_for_planning
created: 2026-07-08
requirements: [REAL-01, REAL-02, REAL-03, REAL-04, REAL-05, REAL-06]
---

# Phase 39 Validation Strategy

## Goal-Backward Truths

Phase 39 is complete only when all of these are true:

1. `saymo auto -p <profile>` cannot enter realtime capture/playback unless the
   shared launch-readiness gate passes for source, cache, cloned voice,
   provider/audio, and call-control handbrake.
2. Existing `saymo auto` usage is preserved while any realtime/call-start alias
   shares the same gate and remediation rendering.
3. Automatic answers fail closed on response-cache miss, stale cloned-voice
   metadata, disabled/unsafe fallback, provider loss, manual takeover,
   hard-disable, or disabled auto-answer.
4. Explicit manual prepared-standup playback remains possible when handbrake
   state allows it, and does not become automatic fallback for question cache
   misses.
5. Realtime decisions expose sanitized reason labels for spoke, skipped, and
   blocked outcomes.
6. Deterministic addressing and handbrake state remain authoritative; live
   assist classifiers or generated wording cannot override a deterministic skip
   or a handbrake block.

## Automated Validation Commands

### Focused Phase 39 Suite

```bash
uv run pytest \
  tests/analysis/test_realtime_gate.py \
  tests/analysis/test_realtime_policy.py \
  tests/test_auto_qa_flow.py \
  tests/test_call_ready_cli.py \
  tests/test_live_control_cli.py \
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

### Static Fail-Closed Guard

```bash
! rg "answer_question\\(|get_selected_tts_engine\\(|synthesize\\(" \
  saymo/analysis/realtime_policy.py \
  saymo/analysis/realtime_gate.py \
  saymo/commands/core.py
```

This guard may need a scoped exception if legacy live-fallback helper code is
kept for non-automatic tests; automatic decision tests must prove it is not
called from the realtime automatic path.

### Static Privacy Guard

```bash
! rg "raw_transcript|generated_answer|answer_text|audio_bytes|PRIVATE_" \
  saymo/analysis/realtime_policy.py \
  saymo/analysis/realtime_gate.py
```

The policy helper may still use `transcript_window` as an input parameter name.
Privacy tests must prove that no serialized decision or event payload contains
a `transcript_window` key or raw transcript value.

### Static Provider/Audio Mutation Guard

```bash
! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill" \
  saymo/analysis/realtime_gate.py \
  saymo/analysis/realtime_policy.py
```

## Required Test Coverage

### REAL-01: Launch Gate Before Realtime

- A shared helper evaluates `collect_launch_readiness()` for the selected
  profile/provider.
- Blocked readiness prevents `_auto` from starting capture, STT warmup,
  provider actions, local hotkey registration, and command-loop tasks.
- Blocked output reuses launch remediation text and returns a stable blocked
  reason.
- Passing readiness allows existing setup to continue.

### REAL-02: Workflow Preservation

- Existing `saymo auto -p standup` remains the command users run.
- Any new alias/wrapper invokes the same helper rather than duplicating checks.
- Tests prove old profile/provider resolution still works.

### REAL-03: Automatic Fail-Closed Policy

- Response-cache hit returns playable cached audio and reason
  `response-cache-hit`.
- Response-cache miss returns a blocked decision, not standup fallback.
- Live fallback / LLM / TTS synthesis is not invoked for automatic playback.
- Stale cloned voice or response-cache metadata blocks automatic playback.
- Provider loss before playback blocks automatic playback.
- Manual takeover, hard-disable, and auto-answer-off block both before
  resolution and immediately before playback.

### REAL-04: Manual Prepared Standup Path

- Manual `speak`/prepared playback remains allowed when handbrake state allows.
- Manual speak uses prepared standup audio intentionally and is labeled
  `manual-standup-requested`.
- Manual speak remains blocked during manual takeover, hard-disable, or active
  speaking.

### REAL-05: Sanitized Decision Reasons

- Decisions expose stable reason/source labels and sanitized metadata only.
- No raw transcript, `transcript_window` serialized key, generated answer,
  daily-note body, audio bytes, or secret appears in decision evidence.
- Existing audit readers remain backward compatible.

### REAL-06: Deterministic Boundary

- Deterministic addressing skip wins before live-assist classifier output.
- Live assist cannot turn a deterministic skip into a speak decision.
- Handbrake state cannot be overridden by response cache, classifier, or
  fallback paths.

## Manual Verification

After automated tests pass, run on the user's machine before trusting a live
call:

```bash
uv run saymo call-ready -p standup --provider glip
uv run saymo call-control-agent status -p standup
uv run saymo call-control probe -p standup
uv run saymo auto -p standup
```

Expected:

- `saymo auto` prints launch readiness failure/remediation and exits if any
  block row is not ready.
- With all rows ready, realtime starts normally.
- During realtime, hard-disable or manual takeover blocks playback before
  audio starts.
- A question with no response-cache hit is skipped/blocked, not answered from
  generated fallback or standup fallback.

## Done Criteria

- Phase 39 focused suite passes.
- Safety regression suite passes.
- Full suite passes.
- Static privacy/fail-closed/provider guards pass or have documented, tested
  scoped exceptions for legacy non-automatic helper code.
- `39-VERIFICATION.md` marks REAL-01 through REAL-06 verified, or documents
  any non-blocking manual live-call residual risk.
